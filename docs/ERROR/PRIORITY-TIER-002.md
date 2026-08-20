# PRIORITY-TIER-002

Tier used against its own semantics.

## Meaning

A `floor` priority declared a decay, or an `opportunistic` priority declared an escalation.

A floor item states that a guarantee the system makes is currently false. That does not
become more acceptable with age, so it must not decay. An opportunistic item is by
definition never allowed to compete for capacity, so escalating it is a contradiction:
it is a request for the tier system to be bypassed rather than used.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Remove the decay from the floor item, or the escalation from the opportunistic one. If the item genuinely needs the other behaviour, it is in the wrong tier.
