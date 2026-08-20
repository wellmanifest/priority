# AMEND

## Purpose

Revise the intent itself when a named condition holds. This is what makes the document a plan for its own change rather than a snapshot.

## Syntax

```
AMEND WHEN <signal> <op> <number> [FOR <duration>]
  REWRITE INTENT "<new sentence>"
  SET TIER <tier>
  SET BASE <number>
  RETIRE
  BECAUSE "<why the intent itself changes>"
```

## Inputs

At least one effect, plus `BECAUSE`. `FOR` requires the condition to have held for a duration before the amendment applies, which stops a metric oscillating around a threshold from rewriting an intent back and forth.

## Outputs

An evaluated priority whose intent, tier, or base has changed, carrying the amendment's reason so the change is visible in the projection.

## Errors

`PRIORITY-AMEND-001`, `PRIORITY-AMEND-002`, `PRIORITY-SIGNAL-003`.

## Examples

```
AMEND WHEN coverage >= 80 FOR 30d
  RETIRE
  BECAUSE "a sustained level is a habit, not a priority"
```

Compare `ON`, which changes only the weight. The separation exists because "this got more urgent" and "this is no longer what we want" are different events, and collapsing them lets a priority quietly become a different priority while keeping its identity and history.
