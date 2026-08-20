# PRIORITY-INTENT-003

Priority with no completion test.

## Meaning

`satisfiedWhen` is required.

A priority that cannot be satisfied can never leave the list. Over time such items
accumulate, and because they never resolve they permanently consume attention that
belongs to work that can actually finish.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Add `SATISFIED_WHEN <signal> <op> <value>` naming a declared signal.
