# crv.io — Canonical IO layer for CRV datasets

Purpose

- Provide a Polars/Arrow-first IO layer for canonical CRV tables defined in `crv.core.tables`.
- Guarantees: append-only writes, atomic tmp→ready file renames, per-table manifests, tick-bucket partitioning, and schema validation.

Key design constraints

- Import DAG: `crv.io` depends only on stdlib, Polars (and pyarrow under the hood), and `crv.core.*`. It MUST NOT import world, mind, lab, viz, or app.
- Layout and semantics align with `plans/io/io_module_starter_plan.md`.

Path layout (file protocol baseline)

- Root is configurable (default: `out`), under which runs are stored:
  - `<root>/runs/<run_id>/tables/<table_name>/bucket=000123/part-<UUID>.parquet`
  - `<root>/runs/<run_id>/tables/<table_name>/manifest.json`
- Partitioning: tick-bucket partitioning with `bucket = tick // tick_bucket_size`.
- `bucket=...` directories zero-padded to 6 digits.

Atomic append semantics

- Writes go to `*.parquet.tmp` first, fsync, then `os.replace(tmp, final)` for atomicity.
- Single-writer initial semantics (no inter-process locks). Per-bucket locking can be added later if needed.

Manifests

- A per-table `manifest.json` tracks partitions (buckets) and parts with:
  - per-part rows, bytes, tick_min, tick_max, and created_at.
  - per-bucket totals: row_count, byte_size, and tick range.
- Readers prune files using manifest tick ranges when a `where` filter is provided.
- If a manifest is missing, readers fall back to an FS walk.
- A `rebuild_manifest_from_fs` utility re-derives manifest data by scanning parquet files (best-effort).

Validation against core descriptors

- Uses `crv.core.tables` as source of truth: required/nullable columns and dtypes.
- Strict mode (default) enforces no extra columns beyond (required ∪ nullable).
- Scalar columns (`i64`, `f64`, `str`) are safely casted when possible.
- `struct` and `list[struct]` accepted as Polars `Struct`/`Object` and `List` respectively (no deep validation in Phase 1).

APIs

- `IoSettings`: configuration (root_dir, tick_bucket_size, row_group_size, compression, strict_schema, etc.)
- `Dataset(settings, run_id)`: facade for a specific run with:
  - `append(table, df, *, validate_schema=True, validate_rows=False) -> dict`
  - `scan(table, where: dict | None = None) -> pl.LazyFrame`
  - `read(table, where: dict | None = None, limit: int | None = None) -> pl.DataFrame`
  - `manifest(table) -> TableManifest | None`
  - `rebuild_manifest(table) -> TableManifest`
- Lower-level helpers in `crv.io.write`, `crv.io.read`, `crv.io.manifest`, `crv.io.paths`, `crv.io.fs`, `crv.io.validate`.

Quickstart

```python
import polars as pl
from crv.io import IoSettings, Dataset
from crv.core.grammar import TableName

# Configure where to write (default: out)
settings = IoSettings(root_dir="out", tick_bucket_size=100)

# Bind to a run
ds = Dataset(settings, run_id="20250101-000000")

# Prepare a minimal identity_edges frame (only required columns)
df = pl.DataFrame({
    "tick": [0, 1, 2, 101],
    "observer_agent_id": ["A0", "A1", "A2", "A0"],
    "edge_kind": ["self_to_object"] * 4,
    "edge_weight": [0.0, 0.1, 0.2, 0.3],
})

# Append atomically; returns a summary
summary = ds.append(TableName.IDENTITY_EDGES, df)
print(summary)

# Scan with pruning (by tick range)
lf = ds.scan(TableName.IDENTITY_EDGES, where={"tick_min": 0, "tick_max": 120})
print(lf.collect())

# Inspect manifest
m = ds.manifest(TableName.IDENTITY_EDGES)
print(m)
```

Configuration (IoSettings)

- `root_dir: str = "out"`
- `partitioning: Literal["tick_buckets"] = "tick_buckets"`
- `tick_bucket_size: int = 100`
- `row_group_size: int = 128 * 1024`
- `compression: Literal["zstd","lz4","snappy"] = "zstd"`
- `strict_schema: bool = True`
- `write_manifest_every_n: int = 1` (reserved for future batching)
- `fs_protocol: str = "file"`, `fs_options: dict = {}` (future fsspec integration)

Config loading (env > TOML > defaults)

IoSettings.load() reads a TOML file (./crv.toml or pyproject.toml under [tool.crv.io]) and then overlays with environment variables. Precedence: environment > TOML > built-in defaults.

TOML examples:

```toml
# crv.toml
[io]
root_dir = "out"
tick_bucket_size = 100
compression = "zstd"
strict_schema = true
write_manifest_every_n = 1
```

```toml
# pyproject.toml
[tool.crv.io]
root_dir = "out"
tick_bucket_size = 100
compression = "zstd"
strict_schema = true
```

Environment variables (prefix CRV*IO*):

```bash
export CRV_IO_ROOT_DIR="out"
export CRV_IO_TICK_BUCKET_SIZE="100"
export CRV_IO_ROW_GROUP_SIZE="131072"
export CRV_IO_COMPRESSION="zstd"          # zstd|lz4|snappy
export CRV_IO_FS_PROTOCOL="file"
export CRV_IO_STRICT_SCHEMA="1"           # 1/0/true/false/yes/no/on/off
export CRV_IO_WRITE_MANIFEST_EVERY_N="1"
```

Run Bundle quickstart

```python
from crv.io.config import IoSettings
from crv.io.run_manifest import write_run_bundle_manifest
from crv.core.ids import RunId

# Resolve settings with precedence (env > TOML > defaults)
settings = IoSettings.load()
run_id = RunId("20250101-000000")

payload = write_run_bundle_manifest(settings, run_id, meta={"note": "demo"})
# Writes: <root>/runs/<run_id>/bundle.manifest.json
print(payload["io"], payload["tables"].keys())
```

Testing

- Unit tests cover:
  - path/bucket math
  - append atomicity and manifest updates
  - scan pruning via manifest ranges
  - manifest rebuild from FS walk
  - strict schema validation
  - import DAG isolation (no side imports of world/mind/lab/viz/app)

Future work

- Optional per-bucket write locks for multi-writer scenarios.
- fsspec-backed remote storage (s3fs/gcsfs).
- Row-level validation and richer struct-type validation.
- Streaming APIs (tail manifest).

Notes

- `crv.io` is designed to be adopted incrementally. Legacy flat outputs remain intact during migration.
