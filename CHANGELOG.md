# Changelog

All notable changes to this project are documented in this file.

## [0.1.0-dev]

- Bootstrap the priority domain pack on wellmanifest/dsl: `DOCUMENT PRIORITY`
  text form, JSON AST, JSON Schema, validator, evaluator, complementarity, and
  agent-facing projections.
- Lexicographic tiers (`floor` / `standard` / `opportunistic`) so that "always
  highest" is structural rather than a large number that erodes as lesser work
  accumulates.
- Separate `ON` (reweights an intent) from `AMEND` (revises the intent itself),
  so a priority cannot quietly become a different priority while keeping its
  identity and history.
- Require `because` on every priority, weight rule, and amendment; require
  `satisfiedWhen` so a priority can leave the list; require a producer on every
  signal so a rank is always traceable to a measurement.
- A missing reading fires nothing by default (`ABSENT hold`): absence of
  evidence must never raise a priority.
- Additive `STARVATION` term with a cap, so development stays even instead of
  pooling in whichever corner is already active.
- Complementarity from path overlap, shared signals, and observed co-movement,
  with declared relations overriding the computation and antagonisms reported
  rather than optimized away.
- Selection ranks sets, not items, with unsatisfied floor items entering as
  constraints.
- Projections to `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules and a JSON
  ranking, spliced into a marked block so surrounding hand-written instructions
  survive; `priority check` gates drift.
