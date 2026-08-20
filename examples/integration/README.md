# Integration examples (non-normative)

Concrete wiring for a specific toolchain. Nothing here is normative — the
standard itself names no tool. These files exist because "declare a producer"
is easy to state and easy to get wrong.

## The three cadences

| File | Cadence | Blocks? |
|---|---|---|
| `pre-commit` | commit | Yes, and only on an unsatisfied `floor` item |
| `priority-sweep.service` + `.timer` | every 5 min | No |
| `priority-watch.sh` | filesystem event | No |

## Producers

A producer prints one number on its last line. That is the whole contract, which
is what lets any quality tool serve as one without knowing this pack exists:

```sh
# a gate that must fail closed, counted from workflow files
grep -rlE 'continue-on-error:\s*true' .github/workflows | wc -l

# artifact digest drift, from whatever integrity checker the repo already has
<integrity-check> --json | jq '[.findings[] | select(.code=="…HASH…")] | length'

# conformance percentage, from the repo's own validator
<validator> --json | jq '.conformance_pct'
```

If a producer fails or times out it yields **no reading**, and a missing reading
fires nothing. A broken tool degrades the ranking's precision, never its
availability, and it must never invent urgency.
