# Control loop — when a document is re-evaluated

A priority document is a pure function of itself plus a set of readings. It is
worth exactly as much as the freshness of those readings, so the standard defines
*when* they are taken, not just how.

## Three cadences, and why not one

| Cadence | Trigger | What it catches | Cost |
|---|---|---|---|
| **Commit** | pre-commit / pre-push hook | The change in front of you violating a floor item | Must stay under a second or it gets bypassed |
| **Interval** | timer, ~5 min | Drift that no commit caused: an expired pin, an external gate going red, a signal window lapsing | Bounded, runs whether or not anyone is working |
| **Watch** | filesystem event on declared surfaces | A `TOUCHES` surface changing, which is what makes churn cooloff and starvation accurate | Near zero when idle |

One cadence is not enough because the three catch disjoint things. A commit hook
never fires on a Friday afternoon when a certificate expires. A five-minute timer
cannot tell you that *this* commit is the one that broke the invariant. A watcher
sees the edit but not the world outside the repository.

## Cost discipline

An adopter-owned runtime resolves declared producer references through an
explicit allowlist. The evaluator never executes them. Producers may be slow, so
two rules keep the runtime honest:

1. **Respect the window.** A signal declares `WINDOW`; the runtime may reuse a
   reading younger than its window rather than re-take it. The evaluator treats
   an older reading as absent.
2. **Never block on a producer.** A producer that fails or times out yields *no
   reading*, and a missing reading fires nothing. A slow tool degrades the
   ranking's precision; it must never degrade its availability, and it must never
   invent urgency.

## What each cadence is allowed to do

All three are read-only with respect to the repository, in keeping with the
propose-only effect model. They differ only in what they may block:

- **Commit** may block, and only on an unsatisfied `floor` item. Blocking a
  commit on a `standard` item trains people to pass `--no-verify`, after which
  the floor items stop being enforced too.
- **Interval** never blocks. It emits fresh readings and a ranking receipt, then
  reports proposed projection drift.
- **Watch** never blocks. It updates freshness inputs — which surfaces were
  touched, and when — that the other two consume.

## The projection step

Every cadence ends the same way: render the proposed agent-facing projection
bytes and report any drift. Applying those bytes is a separate, reviewed effect;
evaluation itself never changes a repository.

## Placement

A watcher or timer is a running process, so it is a `runtime_service` and must
**not** home in a standards repository. This pack defines the contract —
signals, readings, cadences, the propose-only constraint — and stops there. The
process that implements it homes wherever runtime services home.
