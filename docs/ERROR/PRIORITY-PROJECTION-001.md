# PRIORITY-PROJECTION-001

Projection missing or stale.

## Meaning

An agent-facing file does not match the document.

Agents will not converge on one configuration format, so the document is the authority
and each agent file is generated from it. A stale projection is worse than an absent one:
an agent reads it confidently and acts on a ranking that no longer exists.

## Cause

Someone edited an agent file by hand inside the managed block, or the document changed and the projections were not regenerated before committing.

## Resolution

Run `priority project --write` to regenerate, then commit the result. Never hand-edit inside the managed block.
