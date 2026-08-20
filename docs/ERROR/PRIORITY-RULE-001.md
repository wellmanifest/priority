# PRIORITY-RULE-001

Malformed weight rule.

## Meaning

The action is not `RAISE`/`LOWER`, the factor is not positive, or the operator does not
suit the signal kind — numeric comparisons for `metric`, `changed`/`stale` for `event`,
`elapsed` for `schedule`.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Use `RAISE` or `LOWER`, a positive factor, and an operator that suits the signal kind.
