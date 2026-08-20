# Standardization priorities for a fleet that keeps evolving while it is being
# standardized. Abstract: no organization, product, or repository is named.
DOCUMENT PRIORITY
SCHEMA wellmanifest.priority/v1
ID fleet.standardization
VERSION 0.1.0
EFFECT propose-only

SIGNAL gate_fail_open metric "priority-probe gate-fail-open-count"
  UNIT "gates"
  WINDOW 1h
  ABSENT hold

SIGNAL manifest_conformance metric "priority-probe manifest-conformance-pct"
  UNIT "percent"
  WINDOW 6h
  ABSENT hold

SIGNAL adopters metric "priority-probe adopter-count"
  UNIT "repositories"
  WINDOW 24h
  ABSENT hold

SIGNAL digest_drift metric "priority-probe digest-drift-count"
  UNIT "artifacts"
  WINDOW 1h
  ABSENT hold

SIGNAL standard_churn event "docs/STANDARD.md"
  WINDOW 7d

SIGNAL coverage metric "priority-probe coverage-pct"
  UNIT "percent"
  WINDOW 6h
  ABSENT hold

SIGNAL open_claims metric "priority-probe claimed-ticket-count"
  UNIT "tickets"
  WINDOW 15m
  ABSENT zero

SIGNAL sweep schedule "every 5m"
  WINDOW 5m

PRIORITY honest_gates
  TIER floor
  INTENT "Every gate declared fail-closed must actually fail closed."
  BECAUSE "A gate that skips instead of failing makes every conformance signal downstream of it untrustworthy."
  BASE 100
  TOUCHES .github/workflows/**
  TOUCHES scripts/**
  SATISFIED_WHEN gate_fail_open == 0
  ON gate_fail_open > 0 RAISE 2 BECAUSE "a fail-open gate is not a weaker gate, it is the absence of one"
  ON adopters > 3 RAISE 1.5 BECAUSE "blast radius: every adopter inherits the false assurance"
  ESCALATE 1.2 PER 7d

PRIORITY digest_truth
  TIER floor
  INTENT "Recorded artifact digests must match the artifacts."
  BECAUSE "A stale digest silently disables the integrity check it exists to provide."
  BASE 90
  TOUCHES dsl-manifest.json
  SATISFIED_WHEN digest_drift == 0
  ON digest_drift > 0 RAISE 2 BECAUSE "drift compounds: later checks are validated against a lie"
  ESCALATE 1.15 PER 7d

PRIORITY standard_is_abstract
  TIER standard
  INTENT "Keep normative surfaces free of any single adopter's names and paths."
  BECAUSE "A standard whose machine-checkable schema hardcodes its first adopter cannot be adopted by a fourth party."
  BASE 60
  TOUCHES schemas/**
  TOUCHES docs/STANDARD.md
  SATISFIED_WHEN manifest_conformance >= 100
  ON adopters > 1 RAISE 1.6 BECAUSE "each additional adopter multiplies the cost of the coupling"
  ON standard_churn changed 1 LOWER 0.7 BECAUSE "cooloff: the standard was just edited, let it settle before editing again"
  STARVATION 5 PER 14d CAP 30

PRIORITY machine_checkable
  TIER standard
  INTENT "Every normative rule ships with something that can check it."
  BECAUSE "A prose invariant is re-implemented by each adopter and conformance-tested by none."
  BASE 55
  TOUCHES schemas/**
  TOUCHES src/**
  SATISFIED_WHEN manifest_conformance >= 90
  ON manifest_conformance < 50 RAISE 1.8 BECAUSE "unchecked rules diverge fastest while adoption is young"
  ON open_claims > 0 LOWER 0.5 BECAUSE "someone already holds this; a second agent would collide"
  STARVATION 4 PER 14d CAP 24
  AMEND WHEN manifest_conformance >= 90 FOR 14d
    REWRITE INTENT "Keep the conformance suite green and extend it to new rules as they land."
    SET BASE 25
    BECAUSE "once checking exists the work changes kind: from building a checker to maintaining one"

PRIORITY test_depth
  TIER standard
  INTENT "Raise test coverage of the validators to a level that makes refactoring safe."
  BECAUSE "Validators are the load-bearing part; an unverified validator fails silently and in the safe-looking direction."
  BASE 40
  TOUCHES src/**
  TOUCHES tests/**
  SATISFIED_WHEN coverage >= 80
  ON coverage < 40 RAISE 1.5 BECAUSE "below this, a refactor cannot be distinguished from a regression"
  STARVATION 3 PER 21d CAP 15
  AMEND WHEN coverage >= 80 FOR 30d
    RETIRE
    BECAUSE "a sustained level is a habit, not a priority; keeping it listed crowds out real work"

PRIORITY ergonomics
  TIER opportunistic
  INTENT "Smooth the authoring experience for people writing their first document."
  BECAUSE "Adoption friction is real but it is not correctness, and it must never outrank correctness."
  BASE 20
  TOUCHES docs/**
  SATISFIED_WHEN adopters >= 10
  DECAY 0.9 PER 30d

RELATION honest_gates digest_truth complementary 0.7
  BECAUSE "both restore trust in the same integrity chain, and the same CI surface carries them"

RELATION standard_is_abstract machine_checkable complementary 0.8
  BECAUSE "a checker written while decoupling encodes the decoupling; done separately, each redoes the other's analysis"

RELATION standard_is_abstract ergonomics antagonistic -0.4
  BECAUSE "removing a familiar adopter's names from the docs makes the first read harder before it makes it portable"
