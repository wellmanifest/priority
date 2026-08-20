# Complementarity

Priorities are not independent. Ranking them one at a time produces batches whose
members fight each other, and the fight is invisible in the ranking that produced
them.

## Score

`C(a,b) ∈ [-1, 1]`, from three observables kept deliberately separate so a score
can be argued with rather than merely trusted:

| Term | Weight | What it sees | What it misses |
|---|---|---|---|
| **paths** | 0.4 | Jaccard overlap of `TOUCHES` surfaces | Two items on the same files can still pull in opposite directions |
| **signals** | 0.2 | Overlap of the measurements driving them | Shared instrument, unrelated work |
| **observed** | 0.4 | Did satisfying one actually move the other's signal, and which way | Needs history; silent until there is any |

Only `observed` is grounded in outcome. It is the term that catches a pairing
that *looks* complementary — same files, same metric — and is not.

A declared `RELATION` overrides the computation entirely. A human who has looked
at two priorities outranks a similarity score, and the override is recorded as
`source: declared` so the two are never confused.

## Selection

```
score(S) = Σ effective(i) + λ · Σ C(i,j)
subject to: every unsatisfied floor item ∈ S
```

The unit of selection is the **set**. Floor items are constraints rather than
high scorers, which is why they enter the set before optimization rather than
winning it.

## Antagonism is reported, not optimized away

A persistent negative `C` between two standing priorities does not mean the
solver should avoid scheduling them together. It means the two intents disagree,
and the batch is where the disagreement became visible.

Down-weighting the pair hides that. `priority matrix` therefore lists antagonisms
separately, as a question for a human.

## Evenness

Complementarity concentrates work; left alone it concentrates it forever in
whichever corner is already active. The `STARVATION` term is the counterweight: a
surface untouched beyond its declared budget gains weight regardless of how
uninteresting it is.

`CAP` bounds that, because starvation is a nudge toward evenness and not a
mechanism for a dead component to eventually outrank a live invariant.
