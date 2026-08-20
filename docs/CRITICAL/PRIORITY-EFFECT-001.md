# PRIORITY-EFFECT-001

Effect model is not propose-only.

## Risk

A priority document ranks work and explains the ranking. It never authorizes an edit.

This is critical rather than an error because a document that claims the power to apply
changes inverts the trust model: satisfying a priority would stop being a reviewed act,
and the ranking would become a queue of unreviewed writes.

## Detection

The validator reports it on every document whose `effect` is not `propose-only`, and the conformance suite runs the validator.

## Remediation

Set `EFFECT propose-only`. Work that applies changes belongs in a reviewed act downstream of the ranking, not in the document that produces it.

## Verification

```sh
PYTHONPATH=src python3 -m priority validate <document>
```
