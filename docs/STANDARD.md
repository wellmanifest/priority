# wellmanifest/priority — standard

`wellmanifest.priority/v1`

A priority document states **what must be worked on next, how strongly, and what
would change that**. It is abstract: it names no organization, product, or repo.

## 1. Why a DSL and not a list

A ranked list is a photograph. It is correct at the moment it is written and
wrong shortly after, because the thing that determined the ranking — the state of
the code and the environment — keeps moving. Agents then re-derive priorities
from prose, each one differently, and the ranking silently becomes whatever the
last model guessed.

A priority document therefore records two things:

1. **Intent** — the standing direction, with a weight.
2. **The plan by which that intent revises itself** — declared in advance, as
   reactions to named signals.

The second half is what makes it a DSL rather than a config file. `AMEND` blocks
are not a changelog of what happened to the intent; they are the intent's own
statement of how it will change.

## 2. The ordering model

Weight alone cannot express "this must always come first". Any pure score is
outrankable by enough accumulated lesser work, and in practice it always is.

Ordering is therefore **lexicographic across tiers, weighted within a tier**:

| Tier | Meaning | Guarantee |
|---|---|---|
| `floor` | Correctness of the guarantees themselves | No amount of lower-tier weight can outrank a single unsatisfied floor item |
| `standard` | Ordinary weighted work | Ranked by effective weight |
| `opportunistic` | Taken only when floor and standard are clear | Never competes for capacity |

The comparison is `(tier, effective_weight)`, tier first. This is what makes
"always highest" structurally true instead of a large number that erodes.

A `floor` item is not a severity label. It is a claim that the system's stated
guarantees are currently false. The canonical example is a gate that is declared
fail-closed and is observably fail-open: until it is fixed, every conformance
signal downstream of it is untrustworthy, so nothing downstream can be ranked
honestly.

### Escalation and decay

- An unsatisfied `floor` item escalates: its weight grows with age, so it cannot
  be quietly parked.
- An `opportunistic` item decays: an idea nobody has needed for a quarter is
  evidence about the idea.
- A `standard` item does neither by default.

## 3. Effective weight

```
effective = base × Π(modifiers) + starvation
```

Modifiers are declared, never inferred. Each names the signal that drives it, so
a rank can always be explained by pointing at a measurement.

**Raising** — blast radius (how many adopters depend on this), gate staleness,
observed drift, recurrence (the same finding returning), dependency fan-in
(other work is blocked), regression (it was fixed and came back).

**Lowering** — no supporting evidence, work already claimed, cost or uncertainty,
recent churn (a cooloff, so two agents do not thrash the same file), superseded
by a larger item, absent owner.

`starvation` is additive rather than multiplicative, and it is the term that
makes development *even*: a component untouched for longer than its declared
budget gains weight regardless of how uninteresting it is. Without it, a fleet
optimizes into its own hot spots and the rest silently rots.

## 4. Signals

A signal is a named, typed measurement. Three kinds:

- `metric` — a number produced by a quality tool.
- `event` — a filesystem or repository change.
- `schedule` — the passage of time.

Signals are **declared with their producer**, so the document is honest about
where a number comes from and a missing producer is a finding rather than a
silent zero. A rule whose signal has no reading does not fire: absence of
evidence never raises a priority.

## 5. Complementarity

Priorities are not independent, and ranking them one at a time produces batches
that fight each other.

For each pair the document may declare, and a tool may measure:

- **complementary** — doing A makes B cheaper or partly satisfies it.
- **antagonistic** — doing A moves B's signal the wrong way.
- **neutral**.

Measured complementarity `C(a,b) ∈ [-1,1]` combines three observables:

1. **Path overlap** — Jaccard similarity of the paths each priority touches.
   Shared surface is where both the savings and the collisions live.
2. **Shared signals** — priorities driven by the same measurement tend to move
   together.
3. **Co-movement** — over a window, did satisfying A actually move B's signal,
   and in which direction? This is the only term grounded in outcome rather than
   structure, and it is the one that catches a pairing that *looks*
   complementary and is not.

Selection then ranks **sets**, not items:

```
score(S) = Σ effective(i) + λ · Σ C(i,j)   subject to: every unsatisfied floor item ∈ S
```

Antagonistic pairs are not merely down-weighted, they are reported: a persistent
negative `C` between two standing priorities means the two intents disagree, and
that is a question for a human, not an optimization to solve.

## 6. Projection

Agents do not share a configuration format, and no standard will make them. The
document is therefore the authority and every agent-facing file is a
**projection** of it — generated, never hand-edited, and checked for drift.

This is the same rule the ecosystem already applies to descriptions: the
generated artifact is a projection of the AST, and a divergent projection is a
finding.

## 7. Effect model

`propose-only`. A priority document ranks work and explains the ranking. It never
authorizes an edit, and satisfying a priority is always a separate, reviewed act.

## 8. Conformance levels

| Level | Requires |
|---|---|
| `L1 document` | Parses, validates, tiers and weights well formed |
| `L2 signalled` | Every modifier names a signal with a declared producer |
| `L3 projected` | Agent-facing files are generated and drift-checked |
| `L4 measured` | Complementarity computed from observed co-movement, not only declared |
