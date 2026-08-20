from __future__ import annotations

import json
import unittest
from pathlib import Path

import priority as P

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "standardization.priority.dsl"


def doc() -> dict:
    return P.parse(EXAMPLE.read_text(encoding="utf-8"))


class ParseTests(unittest.TestCase):
    def test_example_parses_and_validates(self) -> None:
        self.assertEqual(P.validate(doc()), [])

    def test_projection_round_trips(self) -> None:
        first = doc()
        self.assertEqual(P.parse(P.render(first)), first)

    def test_comments_and_blank_lines_are_ignored(self) -> None:
        text = "# leading\nDOCUMENT PRIORITY\nSCHEMA wellmanifest.priority/v1\n\nID a.b\nVERSION 1.0.0\n"
        self.assertEqual(P.parse(text)["id"], "a.b")

    def test_malformed_duration_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            P.parse_duration("5 days")


class ValidationTests(unittest.TestCase):
    def _doc(self, **overrides):
        base = {
            "schema": P.SCHEMA, "id": "a.b", "version": "1.0.0", "effect": "propose-only",
            "signals": [{"name": "m", "kind": "metric", "producer": "echo 1"}],
            "priorities": [{
                "id": "p", "tier": "standard", "intent": "do x", "because": "evidence",
                "base": 10, "touches": ["src/**"],
                "satisfiedWhen": {"signal": "m", "op": ">=", "value": 1},
                "rules": [], "amendments": [],
            }],
            "relations": [],
        }
        base.update(overrides)
        return base

    def test_clean_document_has_no_findings(self) -> None:
        self.assertEqual(P.validate(self._doc()), [])

    def test_signal_must_name_a_producer(self) -> None:
        d = self._doc(signals=[{"name": "m", "kind": "metric", "producer": ""}])
        self.assertTrue(any(f.code == "PRIORITY-SIGNAL-002" for f in P.validate(d)))

    def test_condition_on_undeclared_signal_is_rejected(self) -> None:
        d = self._doc()
        d["priorities"][0]["satisfiedWhen"] = {"signal": "ghost", "op": ">=", "value": 1}
        self.assertTrue(any(f.code == "PRIORITY-SIGNAL-003" for f in P.validate(d)))

    def test_priority_without_completion_test_is_rejected(self) -> None:
        d = self._doc()
        del d["priorities"][0]["satisfiedWhen"]
        self.assertTrue(any(f.code == "PRIORITY-INTENT-003" for f in P.validate(d)))

    def test_priority_without_evidence_is_rejected(self) -> None:
        d = self._doc()
        d["priorities"][0]["because"] = ""
        self.assertTrue(any(f.code == "PRIORITY-INTENT-002" for f in P.validate(d)))

    def test_floor_must_not_decay(self) -> None:
        d = self._doc()
        d["priorities"][0]["tier"] = "floor"
        d["priorities"][0]["decay"] = {"factor": 0.9, "per": "30d"}
        self.assertTrue(any(f.code == "PRIORITY-TIER-002" for f in P.validate(d)))

    def test_raise_factor_below_one_is_reported(self) -> None:
        d = self._doc()
        d["priorities"][0]["rules"] = [
            {"signal": "m", "op": ">", "value": 0, "action": "RAISE", "factor": 0.5, "because": "why"}
        ]
        self.assertTrue(any(f.code == "PRIORITY-RULE-002" for f in P.validate(d)))

    def test_weight_rule_must_justify_itself(self) -> None:
        d = self._doc()
        d["priorities"][0]["rules"] = [
            {"signal": "m", "op": ">", "value": 0, "action": "RAISE", "factor": 2}
        ]
        self.assertTrue(any(f.code == "PRIORITY-RULE-003" for f in P.validate(d)))

    def test_amendment_must_change_something_and_justify_it(self) -> None:
        d = self._doc()
        d["priorities"][0]["amendments"] = [{"signal": "m", "op": ">=", "value": 1}]
        codes = {f.code for f in P.validate(d)}
        self.assertIn("PRIORITY-AMEND-001", codes)
        self.assertIn("PRIORITY-AMEND-002", codes)

    def test_effect_model_is_locked(self) -> None:
        self.assertTrue(any(f.code == "PRIORITY-EFFECT-001" for f in P.validate(self._doc(effect="apply"))))

    def test_relation_to_unknown_priority_is_rejected(self) -> None:
        d = self._doc(relations=[{"a": "p", "b": "ghost", "kind": "complementary"}])
        self.assertTrue(any(f.code == "PRIORITY-RELATION-001" for f in P.validate(d)))


class OrderingTests(unittest.TestCase):
    def test_a_floor_item_outranks_any_weight_below_it(self) -> None:
        """The point of a tier: no accumulation of lesser weight can cross it."""
        d = doc()
        for item in d["priorities"]:
            if item["id"] == "ergonomics":
                item["base"] = 10 ** 9
        ranked = P.evaluate(d, {"gate_fail_open": P.Reading(value=1)})
        self.assertEqual(ranked[0].tier, "floor")
        self.assertEqual(ranked[-1].id, "ergonomics")

    def test_absent_reading_does_not_fire_a_rule(self) -> None:
        """Absence of evidence must never raise a priority."""
        d = doc()
        with_reading = P.evaluate(d, {"gate_fail_open": P.Reading(value=1), "adopters": P.Reading(value=0)})
        without = P.evaluate(d, {"adopters": P.Reading(value=0)})
        gates_with = next(item for item in with_reading if item.id == "honest_gates")
        gates_without = next(item for item in without if item.id == "honest_gates")
        self.assertGreater(gates_with.effective, gates_without.effective)
        self.assertEqual(gates_without.effective, gates_without.base)

    def test_absent_zero_policy_does_fire(self) -> None:
        d = {
            "schema": P.SCHEMA, "id": "a.b", "version": "1.0.0",
            "signals": [{"name": "m", "kind": "metric", "producer": "x", "absent": "zero"}],
            "priorities": [{
                "id": "p", "tier": "standard", "intent": "i", "because": "b", "base": 10,
                "satisfiedWhen": {"signal": "m", "op": ">", "value": 100},
                "rules": [{"signal": "m", "op": "==", "value": 0, "action": "RAISE", "factor": 3, "because": "w"}],
            }],
        }
        self.assertEqual(P.evaluate(d, {})[0].effective, 30)

    def test_escalation_grows_an_unmet_floor_item(self) -> None:
        d = doc()
        readings = {"gate_fail_open": P.Reading(value=1)}
        fresh = P.evaluate(d, readings, ages={})
        aged = P.evaluate(d, readings, ages={"honest_gates": P.parse_duration("28d")})
        self.assertGreater(
            next(i for i in aged if i.id == "honest_gates").effective,
            next(i for i in fresh if i.id == "honest_gates").effective,
        )

    def test_starvation_lifts_an_untouched_surface(self) -> None:
        """The term that keeps development even instead of pooling in hot spots."""
        d = doc()
        idle = {"standard_is_abstract": P.parse_duration("28d")}
        busy = P.evaluate(d, {}, idle={})
        starved = P.evaluate(d, {}, idle=idle)
        self.assertAlmostEqual(
            next(i for i in starved if i.id == "standard_is_abstract").effective
            - next(i for i in busy if i.id == "standard_is_abstract").effective,
            10.0,
        )

    def test_starvation_respects_its_cap(self) -> None:
        d = doc()
        starved = P.evaluate(d, {}, idle={"standard_is_abstract": P.parse_duration("52w")})
        base = next(i for i in P.evaluate(d, {}) if i.id == "standard_is_abstract").effective
        self.assertAlmostEqual(
            next(i for i in starved if i.id == "standard_is_abstract").effective - base, 30.0
        )

    def test_satisfied_when_marks_completion(self) -> None:
        ranked = P.evaluate(doc(), {"gate_fail_open": P.Reading(value=0)})
        self.assertTrue(next(i for i in ranked if i.id == "honest_gates").satisfied)


class AmendmentTests(unittest.TestCase):
    def test_amendment_rewrites_intent_and_base(self) -> None:
        readings = {"manifest_conformance": P.Reading(value=95, age_seconds=P.parse_duration("20d"))}
        item = next(i for i in P.evaluate(doc(), readings) if i.id == "machine_checkable")
        self.assertTrue(item.intent.startswith("Keep the conformance suite green"))
        self.assertEqual(item.base, 25)
        self.assertTrue(item.amended)

    def test_amendment_holds_until_the_window_elapses(self) -> None:
        readings = {"manifest_conformance": P.Reading(value=95, age_seconds=P.parse_duration("1d"))}
        item = next(i for i in P.evaluate(doc(), readings) if i.id == "machine_checkable")
        self.assertTrue(item.intent.startswith("Every normative rule"))
        self.assertEqual(item.base, 55)

    def test_retire_removes_an_item_from_selection(self) -> None:
        readings = {"coverage": P.Reading(value=85, age_seconds=P.parse_duration("40d"))}
        evaluated = P.evaluate(doc(), readings)
        self.assertTrue(next(i for i in evaluated if i.id == "test_depth").retired)
        chosen = P.select(evaluated, P.complementarity(doc()), capacity=6)
        self.assertNotIn("test_depth", {i.id for i in chosen})


class ComplementarityTests(unittest.TestCase):
    def test_declared_relation_overrides_the_computation(self) -> None:
        matrix = P.complementarity(doc())
        entry = matrix[("machine_checkable", "standard_is_abstract")]
        self.assertEqual(entry["source"], "declared")
        self.assertEqual(entry["score"], 0.8)

    def test_shared_surface_produces_positive_measured_score(self) -> None:
        entry = P.complementarity(doc())[("machine_checkable", "test_depth")]
        self.assertEqual(entry["source"], "measured")
        self.assertGreater(entry["score"], 0)

    def test_observed_comovement_can_flip_a_structural_score(self) -> None:
        pair = ("machine_checkable", "test_depth")
        positive = P.complementarity(doc())[pair]["score"]
        negative = P.complementarity(doc(), comovement={pair: -1.0})[pair]["score"]
        self.assertGreater(positive, 0)
        self.assertLess(negative, 0)

    def test_antagonisms_are_reported_not_hidden(self) -> None:
        found = P.antagonisms(P.complementarity(doc()))
        self.assertEqual([f["pair"] for f in found], [["ergonomics", "standard_is_abstract"]])

    def test_selection_always_includes_unsatisfied_floor_items(self) -> None:
        evaluated = P.evaluate(doc(), {"gate_fail_open": P.Reading(value=1), "digest_drift": P.Reading(value=1)})
        chosen = P.select(evaluated, P.complementarity(doc()), capacity=1)
        self.assertEqual({i.id for i in chosen if i.tier == "floor"}, {"honest_gates", "digest_truth"})

    def test_complementarity_pulls_a_lighter_paired_item_forward(self) -> None:
        """Selection ranks sets: a lighter item that pairs well can beat a heavier loner."""
        anchor = P.Evaluated(id="anchor", tier="standard", intent="", base=100, effective=100, satisfied=False)
        heavy = P.Evaluated(id="heavy", tier="standard", intent="", base=60, effective=60, satisfied=False)
        paired = P.Evaluated(id="paired", tier="standard", intent="", base=50, effective=50, satisfied=False)
        matrix = {("anchor", "paired"): {"score": 1.0}, ("anchor", "heavy"): {"score": -1.0}}

        alone = P.select([anchor, heavy, paired], {}, capacity=2, lam=0.0)
        self.assertEqual({i.id for i in alone}, {"anchor", "heavy"})

        together = P.select([anchor, heavy, paired], matrix, capacity=2, lam=20.0)
        self.assertEqual({i.id for i in together}, {"anchor", "paired"})


class ProjectionTests(unittest.TestCase):
    def test_every_agent_target_is_rendered(self) -> None:
        rendered = P.project(doc(), P.evaluate(doc(), {}))
        self.assertEqual(set(rendered), set(P.PROJECTION_TARGETS.values()))

    def test_managed_block_is_spliced_without_touching_the_rest(self) -> None:
        existing = "# My rules\n\nKeep this line.\n"
        block = P.project_markdown(P.evaluate(doc(), {}))
        merged = P.splice(existing, block)
        self.assertIn("Keep this line.", merged)
        self.assertIn(P.MARKER_BEGIN, merged)
        again = P.splice(merged, block)
        self.assertEqual(merged.count(P.MARKER_BEGIN), 1)
        self.assertEqual(again, merged)

    def test_json_projection_is_machine_readable(self) -> None:
        rendered = P.project(doc(), P.evaluate(doc(), {}))
        payload = json.loads(rendered[".priority/ranking.json"])
        self.assertEqual(payload["document"], "fleet.standardization")
        self.assertTrue(payload["priorities"])

    def test_drift_is_detected_when_a_projection_is_missing(self) -> None:
        import tempfile

        rendered = P.project(doc(), P.evaluate(doc(), {}))
        with tempfile.TemporaryDirectory() as tmp:
            problems = P.drift(Path(tmp), rendered)
        self.assertEqual(len(problems), len(rendered))
        self.assertTrue(all(f.code == "PRIORITY-PROJECTION-001" for f in problems))


class ProbeTests(unittest.TestCase):
    def test_producer_output_becomes_a_reading(self) -> None:
        d = {"signals": [{"name": "m", "kind": "metric", "producer": "x"}]}
        readings = P.probe(d, ROOT, runner=lambda cmd: (0, "42"))
        self.assertEqual(readings["m"].value, 42.0)

    def test_unparseable_producer_output_yields_no_reading(self) -> None:
        d = {"signals": [{"name": "m", "kind": "metric", "producer": "x"}]}
        self.assertIsNone(P.probe(d, ROOT, runner=lambda cmd: (0, "not a number"))["m"].value)

    def test_failing_producer_yields_no_reading(self) -> None:
        d = {"signals": [{"name": "m", "kind": "metric", "producer": "x"}]}

        def boom(cmd):
            raise OSError("no such tool")

        self.assertIsNone(P.probe(d, ROOT, runner=boom)["m"].value)


if __name__ == "__main__":
    unittest.main()


class SchemaAgreementTests(unittest.TestCase):
    """A normative schema nothing executes is a dead schema (AGENTS.md rule 5)."""

    def setUp(self) -> None:
        try:
            import jsonschema  # noqa: F401
        except ImportError:  # pragma: no cover - environment dependent
            self.skipTest("jsonschema not installed")
        self.schema = json.loads((ROOT / "schemas" / "priority.schema.json").read_text())

    def test_valid_example_satisfies_both_validators(self) -> None:
        import jsonschema

        document = doc()
        self.assertEqual(P.validate(document), [])
        jsonschema.validate(document, self.schema)

    def test_invalid_example_is_rejected_by_both(self) -> None:
        import jsonschema

        document = P.parse((ROOT / "examples" / "invalid" / "unsourced-signal.priority.dsl").read_text())
        self.assertTrue(P.validate(document))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(document, self.schema)

    def test_every_declared_finding_code_has_a_help_page(self) -> None:
        manifest = json.loads((ROOT / "dsl-manifest.json").read_text())
        documentation = manifest["documentation"]
        for code in documentation["errorCodes"]:
            self.assertTrue((ROOT / "docs" / "ERROR" / f"{code}.md").exists(), code)
        for code in documentation["criticalCodes"]:
            self.assertTrue((ROOT / "docs" / "CRITICAL" / f"{code}.md").exists(), code)

    def test_every_code_the_validator_emits_is_declared(self) -> None:
        """A finding the manifest does not declare has no help page and no owner."""
        manifest = json.loads((ROOT / "dsl-manifest.json").read_text())
        declared = set(manifest["documentation"]["errorCodes"]) | set(manifest["documentation"]["criticalCodes"])
        emitted = set()
        broken = {
            "schema": "wrong", "id": "BAD", "version": "x", "effect": "apply",
            "signals": [{"name": "s", "kind": "nope", "producer": ""}],
            "priorities": [{"id": "p", "tier": "nope", "base": -1, "rules": [
                {"signal": "ghost", "op": ">", "value": 0, "action": "NOPE", "factor": 1}],
                "amendments": [{"signal": "s", "op": ">", "value": 0}]}],
            "relations": [{"a": "p", "b": "p", "kind": "nope"}],
            "surprise": 1,
        }
        emitted.update(finding.code for finding in P.validate(broken))
        self.assertTrue(emitted)
        self.assertEqual(emitted - declared, set())


class AbstractionTests(unittest.TestCase):
    """The pack must not name any adopter in a normative surface (AGENTS.md rule 1)."""

    NORMATIVE = ["docs/STANDARD.md", "docs/GRAMMAR.md", "docs/COMPLEMENTARITY.md",
                 "docs/TRIGGERS.md", "schemas/priority.schema.json", "src/priority.py"]

    def test_no_adopter_names_in_normative_surfaces(self) -> None:
        forbidden = ("subactor", "semcod", "autogrammar", "wellmanifest/offer")
        for relative in self.NORMATIVE:
            text = (ROOT / relative).read_text().lower()
            for name in forbidden:
                self.assertNotIn(name, text, f"{relative} names {name}")
