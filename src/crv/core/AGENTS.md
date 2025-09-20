# CRV Core – LLM Contribution Playbook

Audience: Automated agents / coding assistants working inside `crv.core`.  
Scope: Grammar, schemas, descriptors, hashing/serde, ids/versioning, constants, errors, tests, and docs that anchor the rest of the CRV stack.

---

## 0. Module Map (authoritative)

Files in `src/crv/core/` and their roles:

- `grammar.py` — enums (`ActionKind`, `ExchangeKind`, `RepresentationEdgeKind`, `TableName`, …), EBNF, normalization helpers (`normalize_visibility`, `*_kind_from_value`, `canonical_action_key`).
- `schema.py` — Pydantic v2 models (payloads, decisions, rows) + validators (lower_snake normalization; `IdentityEdgeRow` combination rules).
- `tables.py` — frozen `TableDescriptor` registry (columns, dtypes, required/nullable, `partitioning=["bucket"]`, `version=SCHEMA_V`).
- `hashing.py` — canonical JSON policy (sorted keys, compact separators, `ensure_ascii=False`) + SHA‑256 helpers.
- `serde.py` — thin `json_loads`, re‑exports `json_dumps_canonical` from `hashing`.
- `ids.py` — NewType IDs (`RunId`, `AgentId`, `TokenId`, `VenueId`, `SignatureId`) + `make_run_id(prefix_[0-9a-f]{6})`.
- `typing.py` — lightweight aliases (`Tick`, `GroupId`, `RoomId`, `JsonDict`).
- `versioning.py` — `SchemaVersion`, `SCHEMA_V`, and helpers (`is_compatible`, `is_successor_of`) + major/minor constants guard.
- `constants.py` — IO‑facing defaults (`TICK_BUCKET_SIZE=100`, `ROW_GROUP_SIZE=128*1024`, `COMPRESSION="zstd"`) consumed downstream by `crv.io`.
- `errors.py` — `GrammarError`, `SchemaError`, `VersionMismatch`.
- `README.md` — human docs for downstream teams (contracts and examples).
- `.specs/` — `spec-0.1.md`, `spec-0.2.md`, ADRs (e.g., `adr-2025-09-20-…`).

Zero‑IO rule: only stdlib + pydantic in this package.

---

## 1. Mission & Non‑Goals

- **Mission:** Keep `crv.core` the single source of truth for CRV semantics—grammar, canonical enums, schema payloads/rows, table descriptors, hashing/serde policy, IDs, versioning constants/metadata, and documentation that other packages rely on (`crv.io`, `crv.world`, `crv.mind`, `crv.viz`, `crv.lab`).
- **Non‑goals:** Do **not** add IO (no Polars/pandas), simulation logic, cognition/world updates, or CLI wiring here. Those belong downstream.

---

## 2. Canonical References (never diverge)

| Topic                 | Source                                         | Notes                                               |
| --------------------- | ---------------------------------------------- | --------------------------------------------------- |
| Naming, schema policy | `src/crv/core/.specs/spec-0.1.md`              | Hard constraints; request a spec update if unclear. |
| Schema/table details  | `src/crv/core/.specs/spec-0.2.md`              | Implementation‑grade blueprint for `schema.py`.     |
| Enum/EBNF definitions | `src/crv/core/grammar.py`                      | Use helpers here—do not re‑declare enums.           |
| Version policy/ADR    | `src/crv/core/.specs/adr-2025-09-20-…`         | Canonical GraphEdit normalization/versioning notes. |
| Contribution protocol | `plans/llm_contribution_rules.md`, root README | Applies to every PR.                                |
| Theory alignment      | `CONCEPT.md`, `concept_docs/*`                 | For “Math mapping” docstrings.                      |

When specs and code disagree, halt and clarify before coding.

---

## 3. Golden Rules (must‑follow)

1. **Naming is sacred**

- Enum classes `PascalCase`; enum members `UPPER_SNAKE`; enum `.value` strings `lower_snake`.
- All field/column names `lower_snake`; EBNF terminals `lower_snake`.

2. **Normalize via grammar helpers**

- `action_kind_from_value`, `exchange_kind_from_value`, `edge_kind_from_value`, `normalize_visibility`, `canonical_action_key`.
- Manual `.lower()` on enum‑like strings is a bug.

3. **Zero‑IO**

- No file/network IO; no third‑party libs beyond pydantic/typing/dataclasses in core.

4. **Docstrings map to math**

- Representation/valuation models include “Math mapping” with canonical symbols.

5. **Identity edges are unified**

- One `identity_edges` table distinguished by `edge_kind` (`RepresentationEdgeKind`).
- Do not add separate identity tables (e.g., `o2o_edges`); downstream can materialize views.

6. **Versioning is centralized**

- Table descriptors MUST use `SCHEMA_V`. Minor = additive/nullable, Major = breaking.
- Keep `SCHEMA_MAJOR_VERSION`/`SCHEMA_MINOR_VERSION` in sync with `SCHEMA_V` (guarded by tests).

7. **Hashing/serde**

- Always use `hashing.json_dumps_canonical`; do not inline `json.dumps` for canonical content.
- Hash helpers: `hash_row`/`hash_context`/`hash_state`.

8. **Contracts reflected in tests**

- Core changes must update tests and docs in the same PR.

9. **Dtype discipline in descriptors**

- Use the restricted set `{"i64","f64","str","struct","list[struct]"}`.
- Booleans encoded as `i64` when required by downstream constraints (e.g., `oracle_calls.cache_hit` as 0/1).

10. **Partitioning discipline**

- Every table has `partitioning=["bucket"]`; `"bucket"` is required and columns include `tick` so bucket can be computed downstream as `tick // TICK_BUCKET_SIZE`.

---

## 4. Module‑Specific Guidance

### 4.1 `grammar.py`

- Source of truth for enums, EBNF, normalization. Extend enums here; update specs and naming tests.
- Provide canonical‑only `PatchOp` set; legacy op names must be rejected.

### 4.2 `ids.py`, `typing.py`

- Use `NewType` for domain IDs. `make_run_id` enforces lower_snake prefix and `^[0-9a-f]{6}$` suffix.

### 4.3 `versioning.py`, `constants.py`

- Document versioning policy; keep `SCHEMA_V` and MAJOR/MINOR constants synchronized.
- Constants are IO‑consumer defaults; change only via spec/ADR.

### 4.4 `hashing.py`, `serde.py`

- Canonical JSON: `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`.
- Do not introduce alternative serializers; `serde` re‑exports `json_dumps_canonical`.

### 4.5 `schema.py`

- Order: payload → decision → rows. Validators normalize enum‑like strings; enforce `IdentityEdgeRow` combination rules via `model_validator`.
- Optional dict/list fields use `Field(default_factory=...)`.
- Clear error messages (`GrammarError` for naming/normalization; `SchemaError` for combos/ranges).

### 4.6 `tables.py`

- `TableDescriptor` is `@dataclass(frozen=True)`.
- Columns `lower_snake`; `partitioning=["bucket"]`; `version=SCHEMA_V`.
- Keep `required ⊆ columns`; `(required ∪ nullable) ⊆ columns`; `required ∩ nullable = ∅`.
- Encode boolean flags as `i64` when constrained by allowed dtype set.

### 4.7 Documentation

- `README.md`: table catalog, schema evolution, examples, test commands.
- Keep `AGENTS.md` aligned with specs and tests; add guardrails when adding enums/tables.

---

## 5. Workflow Checklists

### Before editing

- [ ] Read latest specs (`spec‑0.1`, `spec‑0.2`; relevant ADRs).
- [ ] Confirm no open design questions; coordinate with downstream packages (`crv.io/world/mind/viz/lab`).

### When adding/updating schema models

- [ ] Fields `lower_snake`; enums normalized via grammar; docstring with “Math mapping”.
- [ ] Validators enforce combos (esp. `IdentityEdgeRow`).
- [ ] Example payloads in docstrings; update tests.

### When changing table descriptors

- [ ] Update columns/dtypes + required/nullable + `partitioning=["bucket"]` + `version=SCHEMA_V`.
- [ ] Ensure `"bucket"` is present and required; `tick` present for bucket computation.
- [ ] Update `tests/core/test_tables_descriptors.py` and README table catalog.

### When adding enums/grammar constructs

- [ ] Update `grammar.py` enums + EBNF as needed.
- [ ] Extend naming guard tests to include new enum.
- [ ] Ensure `.value` strings are `lower_snake`; add examples.

### Version bumps

- [ ] Decide Minor (additive) vs Major (breaking).
- [ ] Update `SCHEMA_V`, keep `SCHEMA_MAJOR_VERSION`/`SCHEMA_MINOR_VERSION` in sync.
- [ ] Update descriptors/models/docs/tests in the same PR.
- [ ] Use `is_successor_of` to validate sequential bumps in tests.

### Before merge

- [ ] `uv run ruff check .`
- [ ] `uv run mypy --strict`
- [ ] `uv run pytest -q`
- [ ] Confirm docs/specs/tests reflect behavior; notify downstream of schema changes.

---

## 6. Anti‑Patterns to Block

| Anti‑pattern                            | Why it’s wrong                             | Fix                                                    |
| --------------------------------------- | ------------------------------------------ | ------------------------------------------------------ |
| Manual `.lower()` on enum strings       | Bypasses grammar normalization             | Use `*_kind_from_value` / `normalize_visibility`       |
| New identity tables                     | Violates unified `identity_edges` contract | Use `edge_kind` to distinguish semantics               |
| Inline `json.dumps`/hash computations   | Breaks canonical serialization/hashing     | Use `hashing.json_dumps_canonical` + `hash_*` helpers  |
| Pydantic models without validators      | Accepts bad data silently                  | Add `field_validator`/`model_validator`                |
| Skipping doc/test updates               | Breaks downstream consumers                | Update README/specs/tests in the same PR               |
| Adding third‑party libs/IO in core      | Violates zero‑IO policy                    | Keep core pure (stdlib + pydantic only)                |
| Using unsupported dtypes in descriptors | Breaks IO layer assumptions                | Use `{"i64","f64","str","struct","list[struct]"}` only |
| Writing bool columns in descriptors     | Not in allowed dtype set                   | Encode as `i64` (0/1), e.g., `oracle_calls.cache_hit`  |
| Topology edges inside `identity_edges`  | Mixes world structure with identity/affect | Keep `TopologyEdgeKind` for future world tables only   |
| Legacy O2O GraphEdit operation names    | Contradicts canonical `PatchOp` policy     | Use canonical ops; reject legacy op strings            |

---

## 7. Cross‑Package Integration Notes

- `crv.io` uses descriptors to build Parquet/Arrow schemas and manifests. `"bucket"` must be required, `partitioning=["bucket"]`; `tick` present to compute bucket from `TICK_BUCKET_SIZE`.
- `crv.world` emits rows matching core schema (`identity_edges`, `exchange`, `messages`, `decisions`, `scenarios_seen`, `oracle_calls`).
- `crv.mind` produces `DecisionHead` and `RepresentationPatch` instances validated by core schemas; hashing policy ensures dedupe consistency.
- `crv.viz` expects `edge_kind` and valuation columns stable for dashboards.
- `crv.lab` serializes survey configs and decision traces; keep JSON forward‑compatible.

Note: `oracle_calls.cache_hit` is encoded as `i64` (0/1) by contract; keep this stable for IO/viz.

---

## 8. Review Heuristics (PR checks)

- Field naming and enum values comply with `lower_snake` policy.
- Validators cover all `IdentityEdgeRow` combinations (positive + negative tests).
- Table descriptors: `required ⊆ columns`; `required`/`nullable` disjoint; `partitioning=["bucket"]`; `version==SCHEMA_V`; `"bucket"` required.
- Version constants match `SCHEMA_V` (see `tests/core/test_versioning_constants.py`).
- Hashing/serde policy used consistently.
- README/specs/tests updated in the same PR; downstream notified when schema changes.

---

## 9. Quick Reference Snippets

Identity edge validator template

```python
EDGE_RULES = {
    "self_to_positive_valence": (),
    "self_to_negative_valence": (),
    "self_to_object": ("subject_id", "token_id"),
    "self_to_agent": ("subject_id", "object_id"),
    "agent_to_positive_valence": ("subject_id",),
    "agent_to_negative_valence": ("subject_id",),
    "agent_to_object": ("subject_id", "token_id"),
    "agent_to_agent": ("subject_id", "object_id"),
    "agent_pair_to_object": ("subject_id", "related_agent_id", "token_id"),
    "object_to_positive_valence": ("token_id",),
    "object_to_negative_valence": ("token_id",),
    "object_to_object": ("subject_id", "object_id"),
}
```

Table descriptor helper

```python
from collections.abc import Iterator
_TABLES = {desc.name: desc, ...}

def get_table(name: TableName) -> TableDescriptor:
    return _TABLES[name]

def list_tables() -> Iterator[TableDescriptor]:
    return _TABLES.values()
```

Notes:

- `self_to_agent` (a\_{i,j}) is a primitive self–other tie and should be written explicitly when present.
- Friend/foe channels toward another agent use `agent_to_positive_valence` / `agent_to_negative_valence` with `subject_id=j`.
- Self anchors use `self_to_positive_valence` / `self_to_negative_valence` and require no additional slots (observer is self).

---

## 10. When You’re Stuck

- Specs ambiguous? Pause and open an issue or comment before guessing.
- Precedent missing? Check existing tests and docstrings; follow established patterns.
- Large change touching downstream packages? Draft a migration note in `README.md` and coordinate in advance.

Remember: `crv.core` is the bedrock. Consistency here prevents weeks of rework elsewhere.

---

## 11. GraphEdit Canonical Operations

Allowed operations (canonical only):

- `set_identity_edge_weight`
- `adjust_identity_edge_weight`
- `decay_identity_edges`
- `remove_identity_edge`

Use verbose grammar via `edge_kind` + fields.

Token–token association

```json
{
  "operation": "set_identity_edge_weight",
  "edge_kind": "object_to_object",
  "subject_id": "TokenA",
  "object_id": "TokenB",
  "new_weight": 0.75
}
```

Positive valence trace

```json
{
  "operation": "adjust_identity_edge_weight",
  "edge_kind": "object_to_positive_valence",
  "token_id": "TokenX",
  "delta_weight": 0.1
}
```

Negative valence trace

```json
{
  "operation": "adjust_identity_edge_weight",
  "edge_kind": "object_to_negative_valence",
  "token_id": "TokenX",
  "delta_weight": -0.05
}
```

References:

- `grammar.PatchOp` lists only canonical ops and EBNF terminals.
- `schema.GraphEdit` validator enforces canonical‑only set and `lower_snake` naming.
- `IdentityEdgeRow.edge_kind` uses `RepresentationEdgeKind` with strict combination rules.
