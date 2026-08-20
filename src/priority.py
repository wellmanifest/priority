"""wellmanifest/priority — parse, evaluate, and project priority documents.

Propose-only: this module ranks and explains. It never edits a repository.

The document is deliberately two things at once. A priority states a standing
intent with a weight, and it also states, in advance, how that intent revises
itself when the environment moves. Ranking is then a pure function of the
document plus a set of signal readings, which is what makes a rank explainable:
every number can be traced back to a measurement that was named before it was
taken.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "wellmanifest.priority/v1"
READINGS_SCHEMA = "wellmanifest.priority/readings/v1"
CONTEXT_SCHEMA = "wellmanifest.priority/evaluation-context/v1"
RANKING_SCHEMA = "wellmanifest.priority/ranking/v1"
RANKING_SCHEMA_V2 = "wellmanifest.priority/ranking/v2"

TIERS = ("floor", "standard", "opportunistic")
#: Lexicographic bands. A lower index always outranks a higher one, whatever the
#: weights are; this is what makes "always highest" structural rather than a
#: large number that erodes as lesser work accumulates.
TIER_RANK = {name: index for index, name in enumerate(TIERS)}

SIGNAL_KINDS = ("metric", "event", "schedule")
NUMERIC_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}
EVENT_OPS = ("changed", "stale")
SCHEDULE_OPS = ("elapsed",)
RELATION_KINDS = ("complementary", "antagonistic", "neutral")
ABSENT_POLICIES = ("hold", "zero")

IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
DURATION = re.compile(r"^([0-9]+)([smhdw])$")
_DURATION_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duration(text: str) -> int:
    """Duration in seconds. Raises ValueError so a bad literal is a parse error."""
    match = DURATION.match(text or "")
    if not match:
        raise ValueError(f"malformed duration: {text!r}")
    return int(match.group(1)) * _DURATION_SECONDS[match.group(2)]


def canonical_digest(value: Any) -> str:
    """Return the contract digest of a JSON-compatible value."""
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def document_identity(document: Mapping[str, Any]) -> dict[str, str]:
    """Bind a derived artifact to the exact canonical priority document."""
    return {
        "id": str(document.get("id", "")),
        "version": str(document.get("version", "")),
        "digest": canonical_digest(document),
    }


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ValueError("invalid readings contract")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid readings contract") from exc
    if parsed.tzinfo is None:
        raise ValueError("invalid readings contract")
    return parsed.astimezone(timezone.utc)


@dataclass
class Finding:
    code: str
    message: str
    path: str = "$"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} {self.path}: {self.message}"


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _split_keeping_quotes(rest: str) -> list[str]:
    """Split on whitespace, treating a quoted run as one token."""
    tokens: list[str] = []
    buffer = ""
    in_quotes = False
    escape = False
    for char in rest:
        if escape:
            buffer += char
            escape = False
            continue
        if char == "\\":
            buffer += char
            escape = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            buffer += char
            continue
        if char.isspace() and not in_quotes:
            if buffer:
                tokens.append(buffer)
                buffer = ""
            continue
        buffer += char
    if buffer:
        tokens.append(buffer)
    return tokens


def _number(token: str) -> float:
    return float(token)


def parse(text: str) -> dict[str, Any]:
    """Parse the text projection into the canonical JSON AST."""
    document: dict[str, Any] = {
        "schema": SCHEMA,
        "signals": [],
        "priorities": [],
        "relations": [],
    }
    priority: dict[str, Any] | None = None
    signal: dict[str, Any] | None = None
    amend: dict[str, Any] | None = None
    relation: dict[str, Any] | None = None

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.strip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        head, _, rest = line.strip().partition(" ")
        rest = rest.strip()

        if indent == 0:
            signal = amend = relation = None
            if head == "DOCUMENT":
                continue
            if head == "SCHEMA":
                document["schema"] = rest
            elif head == "ID":
                document["id"] = rest
            elif head == "VERSION":
                document["version"] = rest
            elif head == "EFFECT":
                document["effect"] = rest
            elif head == "SIGNAL":
                name, kind, producer = (_split_keeping_quotes(rest) + ["", "", ""])[:3]
                signal = {"name": name, "kind": kind, "producer": _unquote(producer)}
                document["signals"].append(signal)
                priority = None
            elif head == "PRIORITY":
                priority = {"id": rest, "rules": [], "amendments": [], "touches": []}
                document["priorities"].append(priority)
            elif head == "RELATION":
                tokens = _split_keeping_quotes(rest)
                relation = {"a": tokens[0], "b": tokens[1], "kind": tokens[2]}
                if len(tokens) > 3:
                    relation["strength"] = _number(tokens[3])
                document["relations"].append(relation)
                priority = None
            continue

        if signal is not None and indent == 2:
            if head == "UNIT":
                signal["unit"] = _unquote(rest)
            elif head == "WINDOW":
                signal["window"] = rest
            elif head == "ABSENT":
                signal["absent"] = rest
            continue

        if relation is not None and indent == 2 and head == "BECAUSE":
            relation["because"] = _unquote(rest)
            continue

        if priority is None:
            continue

        if indent == 4 and amend is not None:
            if head == "REWRITE":
                what, _, value = rest.partition(" ")
                if what == "INTENT":
                    amend["rewriteIntent"] = _unquote(value)
            elif head == "SET":
                what, _, value = rest.partition(" ")
                if what == "TIER":
                    amend["setTier"] = value.strip()
                elif what == "BASE":
                    amend["setBase"] = _number(value.strip())
            elif head == "RETIRE":
                amend["retire"] = True
            elif head == "BECAUSE":
                amend["because"] = _unquote(rest)
            continue

        if indent == 2:
            amend = None
            if head == "TIER":
                priority["tier"] = rest
            elif head == "INTENT":
                priority["intent"] = _unquote(rest)
            elif head == "BECAUSE":
                priority["because"] = _unquote(rest)
            elif head == "BASE":
                priority["base"] = _number(rest)
            elif head == "TOUCHES":
                priority["touches"].append(rest)
            elif head == "SATISFIED_WHEN":
                sig, op, value = _split_keeping_quotes(rest)[:3]
                priority["satisfiedWhen"] = {"signal": sig, "op": op, "value": _number(value)}
            elif head == "ON":
                tokens = _split_keeping_quotes(rest)
                rule = {
                    "signal": tokens[0],
                    "op": tokens[1],
                    "value": _number(tokens[2]),
                    "action": tokens[3],
                    "factor": _number(tokens[4]),
                }
                because = _QUOTED.search(rest)
                if because and "BECAUSE" in rest:
                    rule["because"] = _unquote(rest.split("BECAUSE", 1)[1])
                priority["rules"].append(rule)
            elif head == "ESCALATE":
                factor, _, per = rest.partition(" PER ")
                priority["escalate"] = {"factor": _number(factor), "per": per.strip()}
            elif head == "DECAY":
                factor, _, per = rest.partition(" PER ")
                priority["decay"] = {"factor": _number(factor), "per": per.strip()}
            elif head == "STARVATION":
                tokens = _split_keeping_quotes(rest)
                entry = {"points": _number(tokens[0]), "per": tokens[2]}
                if "CAP" in tokens:
                    entry["cap"] = _number(tokens[tokens.index("CAP") + 1])
                priority["starvation"] = entry
            elif head == "AMEND":
                tokens = _split_keeping_quotes(rest)
                # AMEND WHEN <signal> <op> <value> [FOR <duration>]
                amend = {"signal": tokens[1], "op": tokens[2], "value": _number(tokens[3])}
                if "FOR" in tokens:
                    amend["for"] = tokens[tokens.index("FOR") + 1]
                priority["amendments"].append(amend)
    return document


def render(document: Mapping[str, Any]) -> str:
    """Render the AST back to the text projection."""
    lines = ["DOCUMENT PRIORITY", f"SCHEMA {document.get('schema', SCHEMA)}"]
    if document.get("id"):
        lines.append(f"ID {document['id']}")
    if document.get("version"):
        lines.append(f"VERSION {document['version']}")
    lines.append(f"EFFECT {document.get('effect', 'propose-only')}")

    for signal in document.get("signals") or []:
        lines.append("")
        lines.append(f"SIGNAL {signal['name']} {signal['kind']} {_quote(signal.get('producer', ''))}")
        if signal.get("unit"):
            lines.append(f"  UNIT {_quote(signal['unit'])}")
        if signal.get("window"):
            lines.append(f"  WINDOW {signal['window']}")
        if signal.get("absent"):
            lines.append(f"  ABSENT {signal['absent']}")

    for item in document.get("priorities") or []:
        lines.append("")
        lines.append(f"PRIORITY {item['id']}")
        lines.append(f"  TIER {item.get('tier', 'standard')}")
        if item.get("intent"):
            lines.append(f"  INTENT {_quote(item['intent'])}")
        if item.get("because"):
            lines.append(f"  BECAUSE {_quote(item['because'])}")
        if item.get("base") is not None:
            lines.append(f"  BASE {_fmt(item['base'])}")
        for glob in item.get("touches") or []:
            lines.append(f"  TOUCHES {glob}")
        satisfied = item.get("satisfiedWhen")
        if satisfied:
            lines.append(
                f"  SATISFIED_WHEN {satisfied['signal']} {satisfied['op']} {_fmt(satisfied['value'])}"
            )
        for rule in item.get("rules") or []:
            because = f" BECAUSE {_quote(rule['because'])}" if rule.get("because") else ""
            lines.append(
                f"  ON {rule['signal']} {rule['op']} {_fmt(rule['value'])} "
                f"{rule['action']} {_fmt(rule['factor'])}{because}"
            )
        if item.get("escalate"):
            lines.append(f"  ESCALATE {_fmt(item['escalate']['factor'])} PER {item['escalate']['per']}")
        if item.get("decay"):
            lines.append(f"  DECAY {_fmt(item['decay']['factor'])} PER {item['decay']['per']}")
        starvation = item.get("starvation")
        if starvation:
            cap = f" CAP {_fmt(starvation['cap'])}" if starvation.get("cap") is not None else ""
            lines.append(
                f"  STARVATION {_fmt(starvation['points'])} PER {starvation['per']}{cap}"
            )
        for amend in item.get("amendments") or []:
            window = f" FOR {amend['for']}" if amend.get("for") else ""
            lines.append(
                f"  AMEND WHEN {amend['signal']} {amend['op']} {_fmt(amend['value'])}{window}"
            )
            if amend.get("rewriteIntent"):
                lines.append(f"    REWRITE INTENT {_quote(amend['rewriteIntent'])}")
            if amend.get("setTier"):
                lines.append(f"    SET TIER {amend['setTier']}")
            if amend.get("setBase") is not None:
                lines.append(f"    SET BASE {_fmt(amend['setBase'])}")
            if amend.get("retire"):
                lines.append("    RETIRE")
            if amend.get("because"):
                lines.append(f"    BECAUSE {_quote(amend['because'])}")

    for relation in document.get("relations") or []:
        lines.append("")
        strength = f" {_fmt(relation['strength'])}" if relation.get("strength") is not None else ""
        lines.append(f"RELATION {relation['a']} {relation['b']} {relation['kind']}{strength}")
        if relation.get("because"):
            lines.append(f"  BECAUSE {_quote(relation['because'])}")

    lines.append("")
    return "\n".join(lines)


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

DOCUMENT_KEYS = {"schema", "id", "version", "effect", "signals", "priorities", "relations"}
PRIORITY_KEYS = {
    "id", "tier", "intent", "because", "base", "touches", "satisfiedWhen",
    "rules", "escalate", "decay", "starvation", "amendments",
}


def validate(document: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if document.get("schema") != SCHEMA:
        findings.append(Finding("PRIORITY-KIND-001", f"schema must be {SCHEMA}"))
    if document.get("effect", "propose-only") != "propose-only":
        findings.append(Finding("PRIORITY-EFFECT-001", "effect model must be propose-only", "$.effect"))
    if not IDENTIFIER.match(str(document.get("id", ""))):
        findings.append(Finding("PRIORITY-KIND-001", "id must be a stable identifier", "$.id"))
    if not SEMVER.match(str(document.get("version", ""))):
        findings.append(Finding("PRIORITY-KIND-001", "version must be SemVer", "$.version"))
    unknown = sorted(set(document) - DOCUMENT_KEYS)
    if unknown:
        findings.append(Finding("PRIORITY-KIND-001", f"unknown fields {unknown} (unknownPolicy=reject)"))

    signals: dict[str, Mapping[str, Any]] = {}
    for index, signal in enumerate(document.get("signals") or []):
        where = f"$.signals[{index}]"
        name = signal.get("name")
        if not IDENTIFIER.match(str(name or "")):
            findings.append(Finding("PRIORITY-SIGNAL-001", "signal name must be an identifier", where))
        if signal.get("kind") not in SIGNAL_KINDS:
            findings.append(Finding("PRIORITY-SIGNAL-001", f"unknown signal kind {signal.get('kind')!r}", where))
        if not str(signal.get("producer") or "").strip():
            findings.append(
                Finding(
                    "PRIORITY-SIGNAL-002",
                    "a signal must name its producer; an unsourced number cannot justify a rank",
                    where,
                )
            )
        if signal.get("absent") and signal["absent"] not in ABSENT_POLICIES:
            findings.append(Finding("PRIORITY-SIGNAL-001", "absent policy must be hold or zero", where))
        if signal.get("window"):
            try:
                parse_duration(signal["window"])
            except ValueError as error:
                findings.append(Finding("PRIORITY-SIGNAL-001", str(error), where))
        if name in signals:
            findings.append(Finding("PRIORITY-SIGNAL-001", f"duplicate signal {name!r}", where))
        signals[name] = signal

    ids: set[str] = set()
    for index, item in enumerate(document.get("priorities") or []):
        where = f"$.priorities[{index}]"
        item_id = item.get("id")
        if not IDENTIFIER.match(str(item_id or "")):
            findings.append(Finding("PRIORITY-KIND-001", "priority id must be an identifier", where))
        if item_id in ids:
            findings.append(Finding("PRIORITY-KIND-001", f"duplicate priority {item_id!r}", where))
        ids.add(item_id)
        unknown = sorted(set(item) - PRIORITY_KEYS)
        if unknown:
            findings.append(Finding("PRIORITY-KIND-001", f"unknown priority fields {unknown}", where))

        tier = item.get("tier")
        if tier not in TIERS:
            findings.append(Finding("PRIORITY-TIER-001", f"unknown tier {tier!r}", f"{where}.tier"))
        if not str(item.get("intent") or "").strip():
            findings.append(Finding("PRIORITY-INTENT-001", "intent is required", f"{where}.intent"))
        if not str(item.get("because") or "").strip():
            findings.append(
                Finding(
                    "PRIORITY-INTENT-002",
                    "because is required: a priority without stated evidence is a preference",
                    f"{where}.because",
                )
            )
        base = item.get("base")
        if not isinstance(base, (int, float)) or base <= 0:
            findings.append(Finding("PRIORITY-WEIGHT-001", "base must be a positive number", f"{where}.base"))

        if tier == "floor" and item.get("decay"):
            findings.append(
                Finding(
                    "PRIORITY-TIER-002",
                    "a floor priority must not decay: an unmet guarantee does not become acceptable with age",
                    f"{where}.decay",
                )
            )
        if tier == "opportunistic" and item.get("escalate"):
            findings.append(
                Finding("PRIORITY-TIER-002", "an opportunistic priority must not escalate", f"{where}.escalate")
            )

        satisfied = item.get("satisfiedWhen")
        if not satisfied:
            findings.append(
                Finding(
                    "PRIORITY-INTENT-003",
                    "satisfiedWhen is required: a priority with no completion test can never leave the list",
                    f"{where}.satisfiedWhen",
                )
            )
        else:
            findings.extend(_condition_findings(satisfied, signals, f"{where}.satisfiedWhen"))

        for rule_index, rule in enumerate(item.get("rules") or []):
            rule_where = f"{where}.rules[{rule_index}]"
            findings.extend(_condition_findings(rule, signals, rule_where))
            if rule.get("action") not in {"RAISE", "LOWER"}:
                findings.append(Finding("PRIORITY-RULE-001", "action must be RAISE or LOWER", rule_where))
            factor = rule.get("factor")
            if not isinstance(factor, (int, float)) or factor <= 0:
                findings.append(Finding("PRIORITY-RULE-001", "factor must be positive", rule_where))
            elif rule.get("action") == "RAISE" and factor < 1:
                findings.append(Finding("PRIORITY-RULE-002", "RAISE factor below 1 lowers the weight", rule_where))
            elif rule.get("action") == "LOWER" and factor > 1:
                findings.append(Finding("PRIORITY-RULE-002", "LOWER factor above 1 raises the weight", rule_where))
            if not str(rule.get("because") or "").strip():
                findings.append(
                    Finding("PRIORITY-RULE-003", "a weight rule must say why it fires", rule_where)
                )

        for amend_index, amend in enumerate(item.get("amendments") or []):
            amend_where = f"{where}.amendments[{amend_index}]"
            findings.extend(_condition_findings(amend, signals, amend_where))
            effects = [key for key in ("rewriteIntent", "setTier", "setBase", "retire") if amend.get(key)]
            if not effects:
                findings.append(Finding("PRIORITY-AMEND-001", "an amendment must change something", amend_where))
            if amend.get("setTier") and amend["setTier"] not in TIERS:
                findings.append(Finding("PRIORITY-AMEND-001", "unknown tier in amendment", amend_where))
            if not str(amend.get("because") or "").strip():
                findings.append(
                    Finding(
                        "PRIORITY-AMEND-002",
                        "an amendment rewrites the intent itself and must justify that",
                        amend_where,
                    )
                )
            if amend.get("for"):
                try:
                    parse_duration(amend["for"])
                except ValueError as error:
                    findings.append(Finding("PRIORITY-AMEND-001", str(error), amend_where))

    for index, relation in enumerate(document.get("relations") or []):
        where = f"$.relations[{index}]"
        if relation.get("kind") not in RELATION_KINDS:
            findings.append(Finding("PRIORITY-RELATION-001", f"unknown relation {relation.get('kind')!r}", where))
        for side in ("a", "b"):
            if relation.get(side) not in ids:
                findings.append(
                    Finding("PRIORITY-RELATION-001", f"relation names unknown priority {relation.get(side)!r}", where)
                )
        if relation.get("a") == relation.get("b"):
            findings.append(Finding("PRIORITY-RELATION-001", "a priority cannot relate to itself", where))
        strength = relation.get("strength")
        if strength is not None and not -1.0 <= float(strength) <= 1.0:
            findings.append(Finding("PRIORITY-RELATION-001", "strength must lie in [-1, 1]", where))

    return findings


def _condition_findings(
    condition: Mapping[str, Any], signals: Mapping[str, Mapping[str, Any]], where: str
) -> list[Finding]:
    name = condition.get("signal")
    if name not in signals:
        return [
            Finding(
                "PRIORITY-SIGNAL-003",
                f"condition uses undeclared signal {name!r}; declare it with its producer",
                where,
            )
        ]
    kind = signals[name].get("kind")
    op = condition.get("op")
    allowed = NUMERIC_OPS if kind == "metric" else (EVENT_OPS if kind == "event" else SCHEDULE_OPS)
    if op not in allowed:
        return [Finding("PRIORITY-RULE-001", f"operator {op!r} is not valid for a {kind} signal", where)]
    return []


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------


@dataclass
class Reading:
    """One signal observation."""

    value: float | None = None
    # How long the observed condition/event/schedule has been active. This is
    # semantic input for FOR/stale/elapsed and is independent of evidence age.
    age_seconds: float = 0.0
    # How old the observation itself is. SIGNAL WINDOW applies only here.
    observed_age_seconds: float = 0.0
    changed: bool = False
    observed_at: str | None = None
    active_since: str | None = None
    producer_ref: str | None = None


@dataclass(frozen=True)
class ReadingsEnvelope:
    """Validated observations bound to one document and source revision."""

    observed_at: str
    revision: str
    readings: Mapping[str, Reading]
    payload: Mapping[str, Any]

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload)

    def receipt_ref(self) -> dict[str, str]:
        return {
            "digest": self.digest,
            "observedAt": self.observed_at,
            "revision": self.revision,
        }


def load_readings(
    document: Mapping[str, Any], payload: Any
) -> ReadingsEnvelope:
    """Validate and normalize a revision-bound readings/v1 document.

    Producers run outside this library. The evaluator accepts their typed,
    digest-bound observations and rejects unknown signals, producer drift,
    future timestamps, non-finite numbers, and a mismatched document binding.
    """
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema", "document", "observedAt", "revision", "readings"
    }:
        raise ValueError("invalid readings contract")
    if payload.get("schema") != READINGS_SCHEMA:
        raise ValueError("invalid readings contract")

    subject = payload.get("document")
    if not isinstance(subject, Mapping) or set(subject) != {"id", "version", "digest"}:
        raise ValueError("invalid readings contract")
    if dict(subject) != document_identity(document):
        raise ValueError("readings document binding mismatch")

    revision = payload.get("revision")
    if not isinstance(revision, str) or not revision or len(revision) > 240:
        raise ValueError("invalid readings contract")
    envelope_time = _timestamp(payload.get("observedAt"))
    signals = {item["name"]: item for item in document.get("signals") or []}
    raw_readings = payload.get("readings")
    if not isinstance(raw_readings, Mapping):
        raise ValueError("invalid readings contract")

    normalized_payload = {
        "schema": READINGS_SCHEMA,
        "document": dict(subject),
        "observedAt": payload["observedAt"],
        "revision": revision,
        "readings": {},
    }
    readings: dict[str, Reading] = {}
    for name, raw in sorted(raw_readings.items()):
        if name not in signals or not isinstance(raw, Mapping):
            raise ValueError("invalid readings contract")
        if not {"observedAt", "producerRef"} <= set(raw) <= {
            "observedAt", "activeSince", "producerRef", "value", "changed"
        }:
            raise ValueError("invalid readings contract")
        producer = raw.get("producerRef")
        if producer != signals[name].get("producer"):
            raise ValueError("readings producer binding mismatch")
        observed_time = _timestamp(raw.get("observedAt"))
        if observed_time > envelope_time:
            raise ValueError("invalid readings contract")
        active_since = raw.get("activeSince")
        active_time = _timestamp(active_since) if active_since is not None else None
        if active_time is not None and active_time > observed_time:
            raise ValueError("invalid readings contract")
        value = raw.get("value")
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("invalid readings contract")
            value = float(value)
            if not math.isfinite(value):
                raise ValueError("invalid readings contract")
        changed = raw.get("changed", False)
        if not isinstance(changed, bool):
            raise ValueError("invalid readings contract")
        age = max(0.0, (envelope_time - observed_time).total_seconds())
        normalized_item: dict[str, Any] = {
            "observedAt": raw["observedAt"],
            "producerRef": producer,
        }
        if active_since is not None:
            normalized_item["activeSince"] = active_since
        if "value" in raw:
            normalized_item["value"] = value
        if "changed" in raw:
            normalized_item["changed"] = changed
        normalized_payload["readings"][name] = normalized_item
        readings[name] = Reading(
            value=value,
            age_seconds=(
                max(0.0, (envelope_time - active_time).total_seconds())
                if active_time is not None
                else 0.0
            ),
            observed_age_seconds=age,
            changed=changed,
            observed_at=raw["observedAt"],
            active_since=active_since,
            producer_ref=producer,
        )

    return ReadingsEnvelope(
        observed_at=str(payload["observedAt"]),
        revision=revision,
        readings=readings,
        payload=normalized_payload,
    )


@dataclass(frozen=True)
class EvaluationContext:
    """Validated, reproducible time inputs for one evaluation run."""

    observed_at: str
    revision: str
    ages: Mapping[str, float]
    idle: Mapping[str, float]
    payload: Mapping[str, Any]

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload)

    def receipt_ref(self) -> dict[str, str]:
        return {
            "digest": self.digest,
            "observedAt": self.observed_at,
            "revision": self.revision,
        }


def _duration_map(raw: Any, priority_ids: set[str]) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise ValueError("invalid evaluation context")
    if not all(isinstance(identifier, str) for identifier in raw):
        raise ValueError("invalid evaluation context")
    normalized: dict[str, float] = {}
    for identifier in sorted(raw):
        value = raw[identifier]
        if identifier not in priority_ids:
            raise ValueError("evaluation context priority mismatch")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid evaluation context")
        duration = float(value)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("invalid evaluation context")
        normalized[identifier] = duration
    return normalized


def load_evaluation_context(
    document: Mapping[str, Any],
    payload: Any,
    readings: ReadingsEnvelope | None = None,
) -> EvaluationContext:
    """Validate ages and idle durations bound to one document/readings run."""
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema", "document", "readings", "observedAt", "revision", "ages", "idle"
    }:
        raise ValueError("invalid evaluation context")
    if payload.get("schema") != CONTEXT_SCHEMA:
        raise ValueError("invalid evaluation context")
    if payload.get("document") != document_identity(document):
        raise ValueError("evaluation context document binding mismatch")

    expected_readings = readings.receipt_ref() if readings is not None else None
    if payload.get("readings") != expected_readings:
        raise ValueError("evaluation context readings binding mismatch")
    observed_at = payload.get("observedAt")
    observed_time = _timestamp(observed_at)
    if readings is not None and observed_time < _timestamp(readings.observed_at):
        raise ValueError("invalid evaluation context")
    revision = payload.get("revision")
    if not isinstance(revision, str) or not revision or len(revision) > 240:
        raise ValueError("invalid evaluation context")

    priority_ids = {str(item["id"]) for item in document.get("priorities") or []}
    if not priority_ids:
        raise ValueError("invalid evaluation context")
    ages = _duration_map(payload.get("ages"), priority_ids)
    idle = _duration_map(payload.get("idle"), priority_ids)
    normalized_payload = {
        "schema": CONTEXT_SCHEMA,
        "document": document_identity(document),
        "readings": expected_readings,
        "observedAt": observed_at,
        "revision": revision,
        "ages": ages,
        "idle": idle,
    }
    return EvaluationContext(
        observed_at=str(observed_at),
        revision=revision,
        ages=ages,
        idle=idle,
        payload=normalized_payload,
    )


@dataclass
class Evaluated:
    id: str
    tier: str
    intent: str
    base: float
    effective: float
    satisfied: bool
    explanation: list[str] = field(default_factory=list)
    amended: list[str] = field(default_factory=list)
    retired: bool = False

    @property
    def rank_key(self) -> tuple[int, float]:
        """Tier first, weight second. Weight can never cross a tier boundary."""
        return (TIER_RANK.get(self.tier, len(TIERS)), -self.effective)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier,
            "intent": self.intent,
            "base": self.base,
            "effective": round(self.effective, 4),
            "satisfied": self.satisfied,
            "retired": self.retired,
            "explanation": self.explanation,
            "amended": self.amended,
        }


def ranking_receipt(
    document: Mapping[str, Any],
    evaluated: Sequence[Evaluated],
    readings: ReadingsEnvelope | None = None,
) -> dict[str, Any]:
    """Build a deterministic receipt that cannot authorize execution."""
    receipt: dict[str, Any] = {
        "schema": RANKING_SCHEMA,
        "document": document_identity(document),
        "readings": readings.receipt_ref() if readings is not None else None,
        "priorities": [item.as_dict() for item in evaluated],
        "executionAuthorized": False,
    }
    receipt["receiptDigest"] = canonical_digest(receipt)
    return receipt


def ranking_receipt_v2(
    document: Mapping[str, Any],
    context: EvaluationContext,
    readings: ReadingsEnvelope | None = None,
) -> dict[str, Any]:
    """Build a receipt that binds every input affecting deterministic rank."""
    bound_readings = load_readings(document, readings.payload) if readings is not None else None
    bound_context = load_evaluation_context(document, context.payload, bound_readings)
    evaluated = evaluate(
        document,
        bound_readings.readings if bound_readings is not None else None,
        ages=bound_context.ages,
        idle=bound_context.idle,
    )
    receipt: dict[str, Any] = {
        "schema": RANKING_SCHEMA_V2,
        "document": document_identity(document),
        "readings": bound_readings.receipt_ref() if bound_readings is not None else None,
        "context": bound_context.receipt_ref(),
        "priorities": [item.as_dict() for item in evaluated],
        "executionAuthorized": False,
    }
    receipt["receiptDigest"] = canonical_digest(receipt)
    return receipt


def _condition_holds(
    condition: Mapping[str, Any],
    signals: Mapping[str, Mapping[str, Any]],
    readings: Mapping[str, Reading],
) -> bool:
    """True when a condition fires against the current readings.

    A missing reading never fires unless the signal declares ``ABSENT zero``:
    absence of evidence must not raise a priority, or the ranking drifts towards
    whatever is least measured.
    """
    name = condition.get("signal")
    signal = signals.get(name)
    if signal is None:
        return False
    reading = readings.get(name)
    kind = signal.get("kind")

    if reading is not None and signal.get("window"):
        if reading.observed_age_seconds > parse_duration(str(signal["window"])):
            reading = None

    if reading is None or (kind == "metric" and reading.value is None):
        if signal.get("absent", "hold") != "zero":
            return False
        reading = Reading(value=0.0)

    if kind == "metric":
        op = NUMERIC_OPS.get(condition.get("op"))
        return bool(op and op(float(reading.value), float(condition.get("value", 0))))
    if kind == "event":
        if condition.get("op") == "changed":
            return reading.changed
        return reading.age_seconds >= float(condition.get("value", 0))
    return reading.age_seconds >= float(condition.get("value", 0))


def evaluate(
    document: Mapping[str, Any],
    readings: Mapping[str, Reading] | None = None,
    *,
    ages: Mapping[str, float] | None = None,
    idle: Mapping[str, float] | None = None,
) -> list[Evaluated]:
    """Rank the document's priorities against a set of readings.

    ``ages`` is how long each priority has been open, in seconds, and drives
    escalation and decay. ``idle`` is how long the surface a priority touches has
    gone untouched, and drives the starvation term — the term that keeps
    development even instead of letting a fleet optimize into its hot spots.
    """
    readings = dict(readings or {})
    ages = dict(ages or {})
    idle = dict(idle or {})
    signals = {signal["name"]: signal for signal in document.get("signals") or []}

    results: list[Evaluated] = []
    for item in document.get("priorities") or []:
        tier = item.get("tier", "standard")
        intent = item.get("intent", "")
        base = float(item.get("base", 1))
        weight = base
        explanation: list[str] = []
        amended: list[str] = []
        retired = False

        # Amendments run first: they can change the intent the weight applies to.
        for amend in item.get("amendments") or []:
            if not _condition_holds(amend, signals, readings):
                continue
            hold = amend.get("for")
            if hold:
                reading = readings.get(amend["signal"])
                if reading is None or reading.age_seconds < parse_duration(hold):
                    continue
            if amend.get("rewriteIntent"):
                intent = amend["rewriteIntent"]
            if amend.get("setTier"):
                tier = amend["setTier"]
            if amend.get("setBase") is not None:
                base = float(amend["setBase"])
                weight = base
            if amend.get("retire"):
                retired = True
            amended.append(amend.get("because") or f"amended on {amend['signal']}")

        for rule in item.get("rules") or []:
            if not _condition_holds(rule, signals, readings):
                continue
            factor = float(rule.get("factor", 1))
            weight *= factor
            explanation.append(
                f"{rule['action'].lower()} ×{_fmt(factor)} on "
                f"{rule['signal']} {rule['op']} {_fmt(float(rule['value']))}"
                + (f" — {rule['because']}" if rule.get("because") else "")
            )

        age = float(ages.get(item["id"], 0.0))
        escalate = item.get("escalate")
        if escalate and age > 0:
            periods = age / parse_duration(escalate["per"])
            multiplier = float(escalate["factor"]) ** periods
            weight *= multiplier
            explanation.append(f"escalated ×{multiplier:.2f} over {periods:.1f} period(s) unresolved")
        decay = item.get("decay")
        if decay and age > 0:
            periods = age / parse_duration(decay["per"])
            multiplier = float(decay["factor"]) ** periods
            weight *= multiplier
            explanation.append(f"decayed ×{multiplier:.2f} over {periods:.1f} period(s) untaken")

        starvation = item.get("starvation")
        if starvation:
            untouched = float(idle.get(item["id"], 0.0))
            periods = untouched / parse_duration(starvation["per"])
            points = float(starvation["points"]) * periods
            cap = starvation.get("cap")
            if cap is not None:
                points = min(points, float(cap))
            if points > 0:
                weight += points
                explanation.append(f"starvation +{points:.1f} after {periods:.1f} idle period(s)")

        satisfied = False
        condition = item.get("satisfiedWhen")
        if condition and _condition_holds(condition, signals, readings):
            satisfied = True

        results.append(
            Evaluated(
                id=item["id"],
                tier=tier,
                intent=intent,
                base=base,
                effective=weight,
                satisfied=satisfied,
                explanation=explanation,
                amended=amended,
                retired=retired,
            )
        )

    results.sort(key=lambda evaluated: evaluated.rank_key)
    return results


# --------------------------------------------------------------------------
# complementarity
# --------------------------------------------------------------------------


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    left, right = set(a), set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def complementarity(
    document: Mapping[str, Any],
    *,
    comovement: Mapping[tuple[str, str], float] | None = None,
    weights: tuple[float, float, float] = (0.4, 0.2, 0.4),
) -> dict[tuple[str, str], dict[str, float]]:
    """Pairwise complementarity in [-1, 1].

    Three observables, deliberately kept separate so a score can be argued with:

    * ``paths``   — Jaccard overlap of the surfaces two priorities touch. Shared
      surface is where both the savings and the collisions live.
    * ``signals`` — overlap of the measurements that drive them.
    * ``observed``— did satisfying one actually move the other's signal, and in
      which direction. This is the only outcome-grounded term, and the one that
      catches a pairing that looks complementary and is not.

    A declared ``RELATION`` overrides the computation: a human who has looked at
    two priorities outranks a similarity score.
    """
    comovement = dict(comovement or {})
    declared: dict[tuple[str, str], Mapping[str, Any]] = {}
    for relation in document.get("relations") or []:
        declared[tuple(sorted((relation["a"], relation["b"])))] = relation

    items = list(document.get("priorities") or [])
    signals_of = {
        item["id"]: {rule["signal"] for rule in item.get("rules") or []}
        | ({item["satisfiedWhen"]["signal"]} if item.get("satisfiedWhen") else set())
        for item in items
    }
    touches_of = {item["id"]: set(item.get("touches") or []) for item in items}

    matrix: dict[tuple[str, str], dict[str, float]] = {}
    for left_index, left in enumerate(items):
        for right in items[left_index + 1 :]:
            key = tuple(sorted((left["id"], right["id"])))
            paths = _jaccard(touches_of[left["id"]], touches_of[right["id"]])
            shared = _jaccard(signals_of[left["id"]], signals_of[right["id"]])
            observed = float(comovement.get(key, comovement.get(key[::-1], 0.0)))
            score = weights[0] * paths + weights[1] * shared + weights[2] * observed
            entry = {
                "paths": round(paths, 4),
                "signals": round(shared, 4),
                "observed": round(observed, 4),
                "score": round(max(-1.0, min(1.0, score)), 4),
                "source": "measured",
            }
            relation = declared.get(key)
            if relation is not None:
                strength = relation.get("strength")
                if strength is None:
                    strength = {"complementary": 1.0, "antagonistic": -1.0, "neutral": 0.0}[relation["kind"]]
                entry["score"] = round(float(strength), 4)
                entry["source"] = "declared"
                entry["kind"] = relation["kind"]
            matrix[key] = entry
    return matrix


def antagonisms(matrix: Mapping[tuple[str, str], Mapping[str, float]], threshold: float = -0.2) -> list[dict[str, Any]]:
    """Pairs that work against each other.

    Reported rather than silently down-weighted: a standing negative score means
    two intents disagree, which is a question for a human and not an
    optimization to solve.
    """
    return [
        {"pair": list(pair), **dict(entry)}
        for pair, entry in sorted(matrix.items())
        if float(entry.get("score", 0)) <= threshold
    ]


def select(
    evaluated: Sequence[Evaluated],
    matrix: Mapping[tuple[str, str], Mapping[str, float]],
    *,
    capacity: int = 3,
    lam: float = 0.5,
) -> list[Evaluated]:
    """Greedy set selection: weight plus complementarity, floor items mandatory.

    Ranking one item at a time produces batches that fight each other, so the
    unit of selection is the set.
    """
    open_items = [item for item in evaluated if not item.satisfied and not item.retired]
    chosen = [item for item in open_items if item.tier == "floor"]
    remaining = [item for item in open_items if item.tier != "floor"]

    def pair_bonus(candidate: Evaluated, picked: Sequence[Evaluated]) -> float:
        total = 0.0
        for other in picked:
            key = tuple(sorted((candidate.id, other.id)))
            total += float(matrix.get(key, {}).get("score", 0.0))
        return total

    while remaining and len(chosen) < max(capacity, len(chosen)):
        best = max(remaining, key=lambda item: item.effective + lam * pair_bonus(item, chosen))
        chosen.append(best)
        remaining.remove(best)
    return sorted(chosen, key=lambda item: item.rank_key)


# --------------------------------------------------------------------------
# projection to agent-facing files
# --------------------------------------------------------------------------

#: Where each agent reads its standing instructions. Vendors will not converge on
#: one format, so the document is the authority and each of these is generated.
PROJECTION_TARGETS = {
    "agents": "AGENTS.md",          # Codex / ChatGPT, and the ecosystem's own contract
    "claude": "CLAUDE.md",          # Claude Code
    "gemini": "GEMINI.md",          # Gemini CLI
    "cursor": ".cursor/rules/priority.mdc",
    "json": ".priority/ranking.json",  # for CI, hooks, and non-agent consumers
}

MARKER_BEGIN = "<!-- BEGIN wellmanifest.priority -->"
MARKER_END = "<!-- END wellmanifest.priority -->"


def project_markdown(evaluated: Sequence[Evaluated], *, title: str = "Priorities") -> str:
    """The shared body every markdown projection embeds.

    Ordering is explicit and the reason for each rank travels with it: an agent
    that can see why something ranks where it does can tell when the reason has
    stopped applying, which is the whole point of publishing the explanation.
    """
    lines = [
        MARKER_BEGIN,
        f"## {title}",
        "",
        "Generated from the priority document. Do not edit this block by hand:",
        "it is regenerated, and a hand edit is reported as drift.",
        "",
        "Work the tiers in order. A `floor` item outranks every `standard` item",
        "regardless of weight — that is the point of the tier, not a tie-break.",
        "",
    ]
    for tier in TIERS:
        band = [item for item in evaluated if item.tier == tier and not item.retired]
        if not band:
            continue
        lines.append(f"### {tier}")
        lines.append("")
        for item in band:
            state = " *(satisfied)*" if item.satisfied else ""
            lines.append(f"- **{item.id}** — {item.intent}{state}")
            lines.append(f"  - weight {item.effective:.1f} (base {item.base:.0f})")
            for reason in item.explanation:
                lines.append(f"  - {reason}")
            for reason in item.amended:
                lines.append(f"  - amended: {reason}")
        lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def splice(existing: str, block: str) -> str:
    """Replace the managed block in *existing*, or append it.

    Everything outside the markers is left alone: these files carry
    hand-written instructions too, and a projection that overwrote them would
    make itself unwelcome.
    """
    if MARKER_BEGIN in existing and MARKER_END in existing:
        head = existing.split(MARKER_BEGIN, 1)[0]
        tail = existing.split(MARKER_END, 1)[1]
        return head + block + tail
    separator = "" if not existing or existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + separator + block + "\n"


def project(
    document: Mapping[str, Any],
    evaluated: Sequence[Evaluated],
    targets: Mapping[str, str] | None = None,
    readings: ReadingsEnvelope | None = None,
    context: EvaluationContext | None = None,
) -> dict[str, str]:
    """Render every agent-facing projection. Returns {path: content}."""
    targets = dict(targets or PROJECTION_TARGETS)
    block = project_markdown(evaluated)
    out: dict[str, str] = {}
    for name, path in targets.items():
        if name == "json":
            receipt = (
                ranking_receipt_v2(document, context, readings)
                if context is not None
                else ranking_receipt(document, evaluated, readings)
            )
            out[path] = json.dumps(
                receipt, indent=2
            ) + "\n"
        else:
            out[path] = block + "\n"
    return out


def drift(root: Path, rendered: Mapping[str, str]) -> list[Finding]:
    """Report projections that no longer match the document."""
    findings: list[Finding] = []
    for path, content in rendered.items():
        target = root / path
        if not target.exists():
            findings.append(Finding("PRIORITY-PROJECTION-001", f"projection missing: {path}", path))
            continue
        current = target.read_text(encoding="utf-8")
        if path.endswith(".json"):
            if current.strip() != content.strip():
                findings.append(Finding("PRIORITY-PROJECTION-001", f"projection is stale: {path}", path))
            continue
        if MARKER_BEGIN not in current:
            findings.append(Finding("PRIORITY-PROJECTION-001", f"managed block missing from {path}", path))
        elif splice(current, project_markdown_block(content)) != current:
            findings.append(Finding("PRIORITY-PROJECTION-001", f"projection is stale: {path}", path))
    return findings


def project_markdown_block(content: str) -> str:
    """Extract the managed block from a rendered projection."""
    if MARKER_BEGIN in content and MARKER_END in content:
        return MARKER_BEGIN + content.split(MARKER_BEGIN, 1)[1].split(MARKER_END, 1)[0] + MARKER_END
    return content.strip()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return parse(text)


def _report(findings: Sequence[Finding], fmt: str) -> str:
    if fmt == "json":
        return json.dumps([finding.as_dict() for finding in findings], indent=2)
    return "\n".join(str(finding) for finding in findings) or "ok"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="priority", description=__doc__.splitlines()[0])
    parser.add_argument("--format", default="text", choices=["text", "json"])
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "render", "rank", "matrix", "select", "receipt", "project", "check"):
        child = sub.add_parser(name)
        child.add_argument("document", type=Path)
        child.add_argument("--root", type=Path, default=Path("."))
        child.add_argument(
            "--format", choices=("text", "json"), default=argparse.SUPPRESS
        )
        if name in {"rank", "select", "receipt", "project", "check"}:
            child.add_argument(
                "--readings",
                type=Path,
                help="wellmanifest.priority/readings/v1 JSON envelope",
            )
            child.add_argument(
                "--context",
                type=Path,
                help="wellmanifest.priority/evaluation-context/v1 JSON envelope",
            )
        if name == "select":
            child.add_argument("--capacity", type=int, default=3)

    args = parser.parse_args(argv)
    document = _load(args.document)

    findings = validate(document)
    if args.command == "validate":
        print(_report(findings, args.format))
        return 1 if findings else 0
    if findings:
        print(_report(findings, args.format), file=sys.stderr)
        return 1

    if args.command == "render":
        print(render(document))
        return 0

    readings: dict[str, Reading] = {}
    envelope: ReadingsEnvelope | None = None
    if getattr(args, "readings", None):
        raw = json.loads(args.readings.read_text())
        envelope = load_readings(document, raw)
        readings = dict(envelope.readings)

    context: EvaluationContext | None = None
    if getattr(args, "context", None):
        raw_context = json.loads(args.context.read_text())
        context = load_evaluation_context(document, raw_context, envelope)

    evaluated = evaluate(
        document,
        readings,
        ages=context.ages if context is not None else None,
        idle=context.idle if context is not None else None,
    )
    matrix = complementarity(document)

    if args.command == "rank":
        if args.format == "json":
            print(json.dumps([item.as_dict() for item in evaluated], indent=2))
        else:
            for item in evaluated:
                mark = "x" if item.satisfied else " "
                print(f"[{mark}] {item.tier:14s} {item.effective:8.1f}  {item.id} — {item.intent}")
                for reason in item.explanation + item.amended:
                    print(f"                              · {reason}")
        return 0

    if args.command == "matrix":
        payload = {
            "pairs": {f"{a}|{b}": entry for (a, b), entry in sorted(matrix.items())},
            "antagonisms": antagonisms(matrix),
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            for (a, b), entry in sorted(matrix.items()):
                print(f"{entry['score']:+.2f} [{entry['source']:8s}] {a} ~ {b}")
            for item in payload["antagonisms"]:
                print(f"ANTAGONISM {item['pair'][0]} ~ {item['pair'][1]} ({item['score']:+.2f})")
        return 0

    if args.command == "select":
        chosen = select(evaluated, matrix, capacity=args.capacity)
        if args.format == "json":
            print(json.dumps([item.as_dict() for item in chosen], indent=2))
        else:
            for item in chosen:
                print(f"{item.tier:14s} {item.effective:8.1f}  {item.id} — {item.intent}")
        return 0

    if args.command == "receipt":
        receipt = (
            ranking_receipt_v2(document, context, envelope)
            if context is not None
            else ranking_receipt(document, evaluated, envelope)
        )
        print(json.dumps(receipt, indent=2))
        return 0

    rendered = project(document, evaluated, readings=envelope, context=context)
    if args.command == "project":
        if args.format == "json":
            print(json.dumps(rendered, indent=2))
        else:
            for path, content in rendered.items():
                print(f"--- {path}")
                print(content)
        return 0

    problems = drift(args.root, rendered)
    print(_report(problems, args.format))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
