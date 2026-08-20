# AGENTS.md — wellmanifest/priority

HOME wellmanifest, shape domain_pack.
ADOPT wellmanifest/{dsl, new-project, project-ssot}.

## Rules

1. This pack is **abstract**. No organization, product, domain, or repository
   name appears in `docs/STANDARD.md`, `docs/GRAMMAR.md`, `schemas/**`, or
   `src/priority.py`. Concrete adopters live in `examples/` only. A normative
   surface naming an adopter is a defect, not a convenience.
2. `effectModel` is `propose-only` and is not negotiable. The pack ranks and
   explains; it never edits a repository.
3. `unknownPolicy` is `reject`.
4. A watcher, timer, or daemon implementing `docs/TRIGGERS.md` is a
   `runtime_service` and **must not** home here.
5. `schemas/{priority,readings,ranking}.schema.json` are normative sources and
   must stay in agreement with `src/priority.py`. A schema nothing executes is a
   dead schema; the test suite asserts the contracts agree on shipped examples.
6. Every finding code declared in `dsl-manifest.json` has a document under
   `docs/ERROR/` or `docs/CRITICAL/` explaining *why* it is a finding, not only
   what triggered it.
7. Artifact digests in `dsl-manifest.json` are recomputed whenever an owned file
   changes. A stale digest silently disables the integrity check it exists to
   provide.

## Conformance

```sh
PYTHONPATH=src python3 -m priority validate examples/standardization.priority.dsl
PYTHONPATH=src python3 -m unittest discover -s tests
python3 ../dsl/src/dsl_check.py validate --root . dsl-manifest.json
```
