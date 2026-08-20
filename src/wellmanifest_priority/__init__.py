"""Stable package namespace for the Wellmanifest priority reference library.

The historical ``priority`` module remains the CLI implementation for the v1
development line.  Consumers should import this namespace so the implementation
can be split into modules without changing their imports.
"""

from __future__ import annotations

from priority import (
    RANKING_SCHEMA,
    READINGS_SCHEMA,
    SCHEMA,
    Evaluated,
    Finding,
    Reading,
    ReadingsEnvelope,
    antagonisms,
    canonical_digest,
    complementarity,
    document_identity,
    drift,
    evaluate,
    load_readings,
    parse,
    parse_duration,
    project,
    ranking_receipt,
    render,
    select,
    splice,
    validate,
)

__version__ = "0.1.0.dev0"

__all__ = (
    "RANKING_SCHEMA",
    "READINGS_SCHEMA",
    "SCHEMA",
    "Evaluated",
    "Finding",
    "Reading",
    "ReadingsEnvelope",
    "__version__",
    "antagonisms",
    "canonical_digest",
    "complementarity",
    "document_identity",
    "drift",
    "evaluate",
    "load_readings",
    "parse",
    "parse_duration",
    "project",
    "ranking_receipt",
    "render",
    "select",
    "splice",
    "validate",
)
