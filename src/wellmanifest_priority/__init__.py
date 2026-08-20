"""Stable package namespace for the Wellmanifest priority reference library.

The historical ``priority`` module remains the CLI implementation for the v1
development line.  Consumers should import this namespace so the implementation
can be split into modules without changing their imports.
"""

from __future__ import annotations

from priority import (
    CONTEXT_SCHEMA,
    EVALUATION_ATTESTATION_SCHEMA,
    EVALUATION_PREDICATE_TYPE,
    RANKING_SCHEMA,
    RANKING_SCHEMA_V2,
    READINGS_SCHEMA,
    SCHEMA,
    Evaluated,
    EvaluationContext,
    Finding,
    Reading,
    ReadingsEnvelope,
    VerifiedEvaluation,
    antagonisms,
    attestation_signing_bytes,
    canonical_digest,
    complementarity,
    document_identity,
    drift,
    evaluate,
    load_evaluation_context,
    load_readings,
    parse,
    parse_duration,
    project,
    ranking_receipt,
    ranking_receipt_v2,
    render,
    select,
    splice,
    validate,
    verify_evaluation_attestation,
)

__version__ = "0.1.0.dev0"

__all__ = (
    "CONTEXT_SCHEMA",
    "EVALUATION_ATTESTATION_SCHEMA",
    "EVALUATION_PREDICATE_TYPE",
    "RANKING_SCHEMA",
    "RANKING_SCHEMA_V2",
    "READINGS_SCHEMA",
    "SCHEMA",
    "Evaluated",
    "EvaluationContext",
    "Finding",
    "Reading",
    "ReadingsEnvelope",
    "VerifiedEvaluation",
    "__version__",
    "antagonisms",
    "attestation_signing_bytes",
    "canonical_digest",
    "complementarity",
    "document_identity",
    "drift",
    "evaluate",
    "load_evaluation_context",
    "load_readings",
    "parse",
    "parse_duration",
    "project",
    "ranking_receipt",
    "ranking_receipt_v2",
    "render",
    "select",
    "splice",
    "validate",
    "verify_evaluation_attestation",
)
