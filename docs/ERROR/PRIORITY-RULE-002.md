# PRIORITY-RULE-002

Rule direction contradicts its factor.

## Meaning

A `RAISE` with a factor below 1 lowers the weight, and a `LOWER` above 1 raises it.

The document would then read as the opposite of what it does. This is reported rather
than silently honoured because the reader of a priority list is usually not its author.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Flip the action, or invert the factor. `RAISE 1.5` and `LOWER 0.7` are the intended forms.
