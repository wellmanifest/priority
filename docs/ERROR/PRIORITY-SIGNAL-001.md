# PRIORITY-SIGNAL-001

Malformed signal declaration.

## Meaning

The signal name is not an identifier, the kind is not one of `metric`, `event`, `schedule`,
the absent policy is unknown, the window is not a duration, or the name is used twice.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Fix the offending attribute: an identifier name, a kind from `metric|event|schedule`, an absent policy of `hold|zero`, a window such as `6h`, and a name used once.
