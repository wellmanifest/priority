# wellmanifest/priority

`wellmanifest.priority/v1` — standing priorities, the signals that reweight them,
and the amendments by which the intent itself is revised.

Abstract and project-agnostic: this pack names no organization, product, or
repository. Concrete adopters belong in `examples/`.

## The problem

A ranked list of priorities is a photograph. It is correct when written and wrong
shortly after, because the state that justified the ranking keeps moving. Agents
then re-derive priorities from prose — each one differently — and the ranking
quietly becomes whatever the last model guessed.

Three specific failures follow, and the design targets each:

1. **Everything is negotiable.** With a single numeric score, enough accumulated
   small work outranks a correctness invariant. Fixed by **lexicographic tiers**:
   a `floor` item cannot be outranked by any amount of lower-tier weight.
2. **Priorities never die.** Without a completion test an item stays on the list
   forever, consuming attention that belongs to work that can finish. Fixed by
   making `SATISFIED_WHEN` **required**.
3. **The intent silently becomes a different intent.** Fixed by separating
   `ON` (changes the weight) from `AMEND` (changes the intent), and requiring
   an amendment to justify itself.

## Effect model

`propose-only`. The document ranks work and explains the ranking. It never
authorizes an edit.

## Usage

```sh
PYTHONPATH=src python3 -m priority validate examples/standardization.priority.dsl
PYTHONPATH=src python3 -m priority rank    examples/standardization.priority.dsl --readings readings.json
PYTHONPATH=src python3 -m priority matrix  examples/standardization.priority.dsl
PYTHONPATH=src python3 -m priority select  examples/standardization.priority.dsl --capacity 3
PYTHONPATH=src python3 -m priority project examples/standardization.priority.dsl --write
PYTHONPATH=src python3 -m priority check   examples/standardization.priority.dsl   # drift gate
```

## Reaching heterogeneous agents

Claude, ChatGPT/Codex, Gemini and IDE assistants read different files, and no
standard will change that. So the document is the authority and every agent-facing
file is a **generated projection** of it, spliced into a marked block so
hand-written instructions around it survive:

| Target | File |
|---|---|
| Codex / ChatGPT, and the ecosystem contract | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/priority.mdc` |
| CI, hooks, non-agent consumers | `.priority/ranking.json` |

`priority check` fails when a projection drifts, which is what stops the files
from becoming three different rankings.

## Documents

- [`docs/STANDARD.md`](docs/STANDARD.md) — normative model: tiers, weight,
  signals, complementarity, conformance levels.
- [`docs/GRAMMAR.md`](docs/GRAMMAR.md) — the `DOCUMENT PRIORITY` text form.
- [`docs/TRIGGERS.md`](docs/TRIGGERS.md) — commit / interval / watch cadences.
- [`docs/COMPLEMENTARITY.md`](docs/COMPLEMENTARITY.md) — how pairings are measured.

## Conformance

| Level | Requires |
|---|---|
| `document` | Parses and validates |
| `signalled` | Every modifier names a signal with a declared producer |
| `projected` | Agent files generated and drift-checked |
| `measured` | Complementarity computed from observed co-movement, not only declared |
