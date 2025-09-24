# CRV Core

Foundational, zero-IO core for the CRV stack. This module defines:

- Canonical grammar and normalization helpers (enums/EBNF).
- Pydantic v2 models for payloads, decisions, context/persona/affect, and row schemas.
- Table descriptors and a registry tied to the schema version.
- Canonical JSON serialization and hashing helpers.
- Light typed IDs/aliases, constants, and error classes.
- Versioning metadata and compatibility helpers.

Downstream packages (crv.io, crv.world, crv.mind, crv.viz) depend on these contracts.

## Naming and Normalization

- Core uses only stdlib + pydantic. No file/network IO except a minimal read of `core.ebnf` grammar into `grammar.py`.
- Naming policy:
  - Enum classes: PascalCase
  - Enum member names: UPPER_SNAKE (Python)
  - Serialized enum values: lower_snake
  - All field/column names: lower_snake
- Normalization: Free-form string inputs are normalized to canonical lower_snake via helpers in `grammar.py`.
  - `action_kind_from_value`, `exchange_kind_from_value`, `edge_kind_from_value`, `normalize_visibility`, `is_lower_snake`.
- Tests enforce naming via `ensure_all_enum_values_lower_snake([...])`.

See: `src/crv/core/grammar.py`

## Pydantic v2 Schemas

Models reside in `src/crv/core/schema.py`. Key groups:

- Payloads:

  - `Utterance`: act/topic/stance/claims/style/audience.
  - `Interpretation`: event_type/targets/inferred/salience∈[0,1].
  - `AppraisalVector`: valence/arousal/certainty/novelty/goal_congruence∈[0,1].
  - `GraphEdit`: operation in { set_identity_edge_weight, adjust_identity_edge_weight, decay_identity_edges, remove_identity_edge } (canonical-only). `edge_kind` is normalized; use explicit fields:
    - Token–token association: edge_kind="object_to_object", subject_id, object_id
    - Positive trace: edge_kind="object_to_positive_valence", token_id
    - Negative trace: edge_kind="object_to_negative_valence", token_id
    - Optional slots: subject_id/object_id/related_agent_id/token_id; weights or decay_lambda as applicable.
  - `RepresentationPatch`: edits: List[GraphEdit]; energy_delta? (float).

- Decisions:

  - `ActionCandidate`: action_type normalized via `ActionKind`; parameters; score; key.
  - `DecisionHead`: token_value_estimates; action_candidates; abstain; temperature.

- Context/persona/affect:

  - `ScenarioContext`: visibility normalized; optional token_id, labels, channel_name; snapshots.
  - `Persona`: persona_id/label/traits.
  - `AffectState`: valence/arousal/stress defaults within [0,1].

- Rows:
  - `EventEnvelopeRow`: envelope_kind in {"action","observation"}; status in {"pending","executed","rejected"}; visibility normalized.
  - `MessageRow`: visibility normalized; sender/channel/audience/speech_act/topic_label.
  - `ExchangeRow`: `exchange_event_type` normalized via `ExchangeKind`; optional side in {"buy","sell"}; quantity/price.
  - `IdentityEdgeRow` (Unified): `edge_kind` normalized via `RepresentationEdgeKind`; required-fields combination validator (see below).
  - `ScenarioRow`: observer perspective with snapshots; visibility normalized; includes `context_hash`.
  - `DecisionRow`: agent-level decisions (chosen_action/candidates/value estimates).
  - `OracleCallRow`: invocation metadata and hashes (persona/representation/context), timing, cache flags.

### IdentityEdgeRow Combination Rules

Validator enforces required fields by `edge_kind`:

- self_to_positive_valence: — (no additional slots; observer is self)
- self_to_negative_valence: — (no additional slots; observer is self)
- self_to_object: subject_id, token_id
- self_to_agent: subject_id, object_id
- agent_to_positive_valence: subject_id
- agent_to_negative_valence: subject_id
- agent_to_object: subject_id, token_id
- agent_to_agent: subject_id, object_id
- agent_pair_to_object: subject_id, related_agent_id, token_id
- object_to_positive_valence: token_id
- object_to_negative_valence: token_id
- object_to_object: subject_id, object_id

This unifies identity edge logging into a single table `identity_edges`.

## Quick examples

GraphEdit (canonical operations)

```python
from crv.core.schema import GraphEdit, RepresentationPatch

# Token–token association
e1 = GraphEdit(
    operation="set_identity_edge_weight",
    edge_kind="object_to_object",
    subject_id="TokenA",
    object_id="TokenB",
    new_weight=0.75,
)

# Positive valence trace
e2 = GraphEdit(
    operation="adjust_identity_edge_weight",
    edge_kind="object_to_positive_valence",
    token_id="Alpha",
    delta_weight=0.1,
)

patch = RepresentationPatch(edits=[e1, e2])
```

IdentityEdgeRow (minimal valid payloads)

```python
from crv.core.schema import IdentityEdgeRow

# object_to_positive_valence requires token_id
row1 = IdentityEdgeRow(
    tick=1,
    observer_agent_id="agent_1",
    edge_kind="object_to_positive_valence",
    token_id="Alpha",
    edge_weight=0.6,
)

# agent_to_object requires subject_id, token_id
row2 = IdentityEdgeRow(
    tick=1,
    observer_agent_id="agent_1",
    edge_kind="agent_to_object",
    subject_id="agent_2",
    token_id="Alpha",
    edge_weight=0.4,
)
```

## Grammar and EBNF

`grammar.py` defines enums:

- `ActionKind`, `ChannelType`, `Visibility`, `PatchOp`,
  `RepresentationEdgeKind`, `TopologyEdgeKind` (future), `ExchangeKind`, `TableName`.

Lower_snake EBNF and helpers:

- `EBNF_GRAMMAR` (lower_snake authoritative terminals; see `crv.core.grammar.EBNF_GRAMMAR`)
- Helpers: `is_lower_snake`, `assert_lower_snake`, `normalize_visibility`, `canonical_action_key`, etc.
- Test utility: `ensure_all_enum_values_lower_snake`.

## Table Catalog

Descriptors live under `src/crv/core/tables/` as frozen `TableDescriptor` instances; the `tables` package `__init__.py` registers them into a canonical registry.
All tables include `bucket` (partitioning key; computed in IO as `tick // TICK_BUCKET_SIZE`) and `version=SCHEMA_V`.

- exchange

  - Purpose: Generalized exchange events (trade/order/swap/gift/vote).
  - Key columns: tick, venue_id, token_id, exchange_event_type, side?, quantity?, price?, actor/counterparty?, baseline_value?, additional_payload (struct).

- identity_edges (Unified representation edges)

  - Purpose: Snapshot/delta rows of edges inside an agent’s internal representation.
  - Key columns: tick, observer_agent_id, edge_kind, subject_id?, object_id?, related_agent_id?, token_id?, edge_weight, edge_sign?.

- holdings

  - Purpose: Quantity snapshot of conserved resources per (tick, agent_id, token_id). Optional per ADR-003 when the domain models a conserved per-token resource.
  - Key columns: tick, agent_id, token_id, quantity.

- holdings_valuation (TODO)

- scenarios_seen

  - Purpose: Observer-centric scenario context snapshots used in valuation/decision.
  - Key columns: tick, observer_agent_id, token_id?, visibility_scope?, salient_agent_pairs (list[struct]), exchange_snapshot (struct), recent_affect_index?, salient_other_agent_id?, context_hash.

- messages

  - Purpose: Communication events emitted by agents.
  - Key columns: tick, sender_agent_id, channel_name, visibility_scope, audience (struct), speech_act, topic_label, stance_label?, claims (struct), style (struct).

- decisions

  - Purpose: Agent decision outputs per tick.
  - Key columns: tick, agent_id, chosen_action (struct), action_candidates (list[struct]), token_value_estimates (struct).

- oracle_calls
  - Purpose: LLM/tooling calls with persona/context and cache metadata.
  - Key columns: tick, agent_id, engine, signature_id, persona_id, persona_hash, representation_hash, context_hash, value_json, latency_ms, cache_hit (i64), n_tool_calls (i64), tool_seq (struct).

APIs:

- `get_table(name: TableName) -> TableDescriptor`
- `list_tables() -> list[TableDescriptor]`

## Versioning and Schema Evolution

- Canonical version: `src/crv/core/versioning.py`
  - `SchemaVersion` (frozen dataclass)
  - `SCHEMA_V`: current = (0, 1, "2025-09-20")
  - Helpers: `is_compatible(ver)`, `is_successor_of(candidate, current)`

Policy:

- Major: breaking changes; Minor: additive, non-breaking changes.
- During development of a feature sprint, keep `SCHEMA_V` unchanged until feature completion is approved.
- When bumping:
  1. Update `SCHEMA_V`.
  2. Update descriptors/models/tests/docs in the same change.
  3. Use `is_successor_of` to validate sequential bumps.

## Hashing and Serde (Canonical JSON)

- `hashing.json_dumps_canonical(obj)`:
  - `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`
- `hashing.hash_row(row)`, `hash_context(ctx_json)`, `hash_state(agent_state)`:
  SHA-256 hex digest over canonical JSON.
- `serde.json_loads(s: str)` thin wrapper around stdlib; re-exports `json_dumps_canonical` for a single canonicalization policy.

## IDs, Typing, and Constants

- `ids.py`: `RunId`, `AgentId`, `TokenId`, `VenueId`, `SignatureId`; `make_run_id(prefix="run") -> RunId` yields `<prefix>_[0-9a-f]{6}` with lower_snake prefix enforcement.
- `typing.py`: `Tick`, `GroupId`, `RoomId`, `JsonDict`.
- `constants.py` (consumed by crv.io):
  - `TICK_BUCKET_SIZE = 100`
  - `ROW_GROUP_SIZE = 128 * 1024`
  - `COMPRESSION = "zstd"`

## Errors

Domain-specific exceptions in `errors.py`:

- `GrammarError` for grammar/naming violations (e.g., not lower_snake).
- `SchemaError` for schema-level validation failures (ranges, cross-field constraints).
- `VersionMismatch` for schema version incompatibilities.

## Design Notes

- Identity edges unified:
  - All representation edges persist to a single `identity_edges` table distinguished by `edge_kind` (RepresentationEdgeKind) with combination rules enforced by validators.
  - Downstream readers should filter by `edge_kind` to reconstruct specific edge families (self_to_object, agent_to_agent, etc.).
  - Concept-doc cross-ref: some design docs list separate `o2o_edges` and `o2o_obj` tables; in core these are represented within `identity_edges` via `edge_kind` ∈ {`agent_to_agent`,`agent_pair_to_object`}. Downstream may materialize split views if desired.
- IO alignment:
  - All descriptors include `bucket` and `partitioning=["bucket"]`; IO layers compute/populate bucket from tick using `TICK_BUCKET_SIZE`.
  - Compression defaults to `"zstd"`; adjust only via spec update.

## Tests

Core tests (see `tests/core/`):

- Grammar naming: all enum `.value` are lower_snake.
- IdentityEdgeRow combination matrix (positive/negative cases).
- ExchangeRow normalization; visibility normalization for MessageRow/ScenarioRow.
- Table descriptor contract (columns lower_snake; required/nullable; partitioning; version pinned).
- Decision schemas (ActionCandidate normalization; DecisionHead defaults).
- Hashing/serde stability (order-insensitive canonical dumps; hash equality).

How to run locally:

```bash
uv run ruff check .
uv run mypy --strict
uv run pytest -q
```

All core tests pass on CI (pytest).
