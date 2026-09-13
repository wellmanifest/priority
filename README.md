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
python3 -m pip install -e .
priority validate examples/standardization.priority.dsl
priority rank    examples/standardization.priority.dsl --readings examples/readings.demo.json
priority receipt examples/standardization.priority.dsl \
  --readings examples/readings.demo.json \
  --context examples/evaluation-context.demo.json
priority matrix  examples/standardization.priority.dsl
priority select  examples/standardization.priority.dsl --capacity 3
priority project examples/standardization.priority.dsl   # proposed bytes only
priority check   examples/standardization.priority.dsl   # drift gate
```

The evaluator accepts only a versioned `wellmanifest.priority/readings/v1`
envelope bound to the exact document digest and producer references. It never
executes those producers. A runtime integration may run an explicit allowlist,
then pass its observations to the pure evaluator. `observedAt` controls reading
freshness; optional `activeSince` records how long a condition has held.

Independent producers may emit partial readings envelopes. `compose_readings`
combines disjoint, validated envelopes and emits a
`wellmanifest.priority/readings-composition/v1` receipt binding every source
digest and revision to the final readings digest. Duplicate signals and source
observations newer than the composition time fail closed.

`priority receipt` emits a deterministic `wellmanifest.priority/ranking/v1`
receipt. It is digest-bound and always carries `executionAuthorized: false`.

Escalation, decay and starvation additionally depend on elapsed durations. A
runtime that supplies them uses a
`wellmanifest.priority/evaluation-context/v1` envelope bound to the exact
document and readings revision. Passing `--context` emits
`wellmanifest.priority/ranking/v2`, whose receipt binds every input that can
change the rank. V1 remains available for evaluations that do not supply this
time context.

An external runtime may sign an
`wellmanifest.priority/evaluation-attestation/v1` over the exact document,
readings, context and ranking v2 digest. The reference verifier requires an
allowlisted issuer implementation digest, audience, current 15-minute validity
window, unused nonce and a caller-provided protected signature verifier. The
attestation remains `executionAuthorized: false`; it proves provenance and
reproducibility, not permission to execute work.

## Reaching heterogeneous agents

Claude, ChatGPT/Codex, Gemini and IDE assistants read different files, and no
standard will change that. So the document is the authority and every agent-facing
file is a **generated projection** of it. `priority project` only proposes the
exact output bytes. An adopter-owned workflow may review and splice the marked
block so hand-written instructions around it survive:

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
