"""
Core package aggregator for CRV contracts (grammar, schemas, tables, hashing/serde, ids, versioning).

Provides a single, auditable source of truth for the CRV stack's contracts:
- Grammar (enums, EBNF, normalization helpers).
- Typed schemas (payloads, decisions, rows) with validators.
- Table descriptors (for IO backends to materialize datasets).
- Canonical JSON and hashing utilities.
- Typed IDs/aliases and schema versioning metadata.

Notes:
    - Zero-IO policy: stdlib + pydantic only; no file/network IO.
    - Naming policy: enum `.value` and field/column names are lower_snake.
    - Canonical-only GraphEdit operations are enforced (see schema.GraphEdit).
    - Unified identity_edges table: differentiate semantics via `edge_kind`.

Downstream usage:
    - crv.io:
        Builds Parquet/Arrow schemas/manifests from `tables` and validates rows
        produced by other packages against `schema` models.
    - crv.world:
        Emits rows conforming to core `schema` (e.g., identity_edges, exchange)
        using normalization helpers from `grammar`.
    - crv.mind:
        Produces `DecisionHead` and `RepresentationPatch` instances validated by
        core schemas and serialized using canonical JSON for hashing.
    - crv.lab / crv.viz:
        Import enums and row models for typed EDSL tasks and dashboards; rely on
        `edge_kind` (RepresentationEdgeKind) to filter identity edges.

Examples:
    Basic normalization, key building, and schema validation.

    >>> from crv.core.grammar import ActionKind, action_kind_from_value, canonical_action_key
    >>> action_kind_from_value("acquire_token") == ActionKind.ACQUIRE_TOKEN
    True
    >>> canonical_action_key(ActionKind.ACQUIRE_TOKEN, token_id="Alpha")
    'acquire_token:token_id=Alpha'

    Create a typed identity edge row (unified identity_edges).

    >>> from crv.core.schema import IdentityEdgeRow
    >>> row = IdentityEdgeRow(
    ...     tick=1,
    ...     observer_agent_id="i1",
    ...     edge_kind="object_to_positive_valence",
    ...     token_id="Alpha",
    ...     edge_weight=0.6,
    ... )
    >>> row.edge_kind
    'object_to_positive_valence'

References:
    - Grammar and helpers: src/crv/core/grammar.py
    - Schemas: src/crv/core/schema.py
    - Tables: src/crv/core/tables.py
    - Hashing/serde: src/crv/core/hashing.py, src/crv/core/serde.py
    - IDs/typing: src/crv/core/ids.py, src/crv/core/typing.py
    - Versioning/constants/errors: src/crv/core/versioning.py, src/crv/core/constants.py, src/crv/core/errors.py
"""
