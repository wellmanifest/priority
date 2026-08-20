# PRIORITY

## Purpose

Declare one standing priority: what should be true, why it matters, how strongly it ranks, and what would change that.

## Syntax

```
PRIORITY <identifier>
  TIER floor | standard | opportunistic
  INTENT "<one sentence>"
  BECAUSE "<evidence>"
  BASE <number>
  TOUCHES <glob>
  SATISFIED_WHEN <signal> <op> <number>
  ON <signal> <op> <number> RAISE|LOWER <factor> BECAUSE "<why>"
  ESCALATE <factor> PER <duration>
  DECAY <factor> PER <duration>
  STARVATION <points> PER <duration> CAP <points>
```

## Inputs

`TIER`, `INTENT`, `BECAUSE`, `BASE` and `SATISFIED_WHEN` are required. `TOUCHES` is repeatable and names the surface this work edits; it drives measured complementarity and churn cooloff.

`ESCALATE` is available to `floor` only, `DECAY` to `opportunistic` only.

## Outputs

An entry in the evaluated ranking, carrying its effective weight and the list of rules that produced it.

## Errors

`PRIORITY-TIER-001`, `PRIORITY-TIER-002`, `PRIORITY-INTENT-001`, `PRIORITY-INTENT-002`, `PRIORITY-INTENT-003`, `PRIORITY-WEIGHT-001`, `PRIORITY-RULE-001`, `PRIORITY-RULE-002`, `PRIORITY-RULE-003`.

## Examples

See `examples/standardization.priority.dsl`.
