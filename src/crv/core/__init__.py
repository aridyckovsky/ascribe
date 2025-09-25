"""
Core package aggregator for CRV contracts (grammar, schemas, tables, hashing/serde, ids, versioning).

## Contracts (single source of truth)
- Grammar — enums, EBNF, normalization helpers.
- Schemas — typed models (payloads, decisions, rows) with validators.
- Tables — descriptors for IO backends to materialize datasets.
- Hashing/Serde — canonical JSON utilities.
- IDs/Versioning — typed IDs, schema version metadata.

## Notes
- Zero‑IO policy: stdlib + pydantic only; no file/network IO.
- Naming policy: enum `.value` and field/column names are lower_snake.
- GraphEdit: canonical‑only operations enforced (see schema.GraphEdit).
- identity_edges unified table: differentiate semantics via `edge_kind`.

## Downstream usage
- crv.io — builds Parquet/Arrow schemas/manifests from `tables` and validates rows against `schema`.
- crv.world — emits rows conforming to core `schema` (e.g., identity_edges, exchange) using `grammar`.
- crv.mind — produces `DecisionHead` and `RepresentationPatch` instances; serializes via canonical JSON for hashing.
- crv.lab / crv.viz — import enums/row models for EDSL tasks and dashboards; rely on `edge_kind` to filter identity edges.

## Examples
```python
# Basic normalization, key building, and schema validation.
from crv.core.grammar import ActionKind, action_kind_from_value, canonical_action_key
action_kind_from_value("acquire_token") == ActionKind.ACQUIRE_TOKEN  # True
canonical_action_key(ActionKind.ACQUIRE_TOKEN, token_id="Alpha")  # 'acquire_token:token_id=Alpha'

# Create a typed identity edge row (unified identity_edges).
from crv.core.schema import IdentityEdgeRow
row = IdentityEdgeRow(
    tick=1,
    observer_agent_id="i1",
    edge_kind="object_to_positive_valence",
    token_id="Alpha",
    edge_weight=0.6,
)
row.edge_kind  # 'object_to_positive_valence'
```

## References
- Grammar and helpers: [grammar](grammar.md)
- Schemas: [schema](schema.md)
- Tables: [tables](tables/index.md)
- Hashing/Serde: [hashing](hashing.md), [serde](serde.md)
- IDs/Typing: [ids](ids.md), [typing](typing.md)
- Versioning/Constants/Errors: [versioning](versioning.md), [constants](constants.md), [errors](errors.md)
"""
