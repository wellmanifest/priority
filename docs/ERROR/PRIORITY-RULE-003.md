# PRIORITY-RULE-003

Weight rule without justification.

## Meaning

Each rule says why it fires. The reason travels into the agent-facing projection, so a
reader can tell when the reason has stopped applying — which is the only reliable way a
standing rule ever gets retired.

## Cause

The document declares something the model does not permit; the surrounding text of the document usually shows which edit introduced it.

## Resolution

Add `BECAUSE "..."` saying what the rule is responding to.
