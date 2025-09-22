# CRV IO

Canonical Polars/Arrow‑first IO for CRV datasets. Aligns with `crv.core.tables` and enforces append‑only semantics, atomic renames, per‑table manifests, tick‑bucket partitioning, and schema validation.

## At a Glance

- Append‑only, atomic writes (`*.tmp` → fsync → atomic rename).
- Per‑table manifests with bucket/part metadata and tick ranges.
- Manifest‑guided pruning on reads (by tick range).
- Validation against core descriptors (strict by default).
- Import DAG: stdlib, Polars/Arrow, and `crv.core.*` only.

## Scope & Guarantees

- Append‑only writer (single‑writer initial semantics; per‑bucket locks can be added later).
- Partitioning: `bucket = tick // tick_bucket_size`, directories zero‑padded (e.g., `bucket=000123`).
- Manifests record per‑part and per‑bucket stats for reader pruning.
- Strict schema mode:
  - No columns beyond (required ∪ nullable).
  - Safe scalar casts to (`i64`, `f64`, `str`).
  - `Struct` / `List[Struct]` accepted (Phase 1: shallow checks).

## Path Layout

```
<root>/runs/<run_id>/tables/<table_name>/
  bucket=000123/part-<UUID>.parquet
  manifest.json
```

`root_dir` is configurable via `IoSettings` (default: `out`).

## Append Semantics

- Write to `*.parquet.tmp`, fsync file & directory, then `os.replace(tmp → final)` atomically.

## Manifests

Each table’s `manifest.json` includes:

- Per‑part: `rows`, `bytes`, `tick_min`, `tick_max`, `created_at`.
- Per‑bucket: `row_count`, `byte_size`, tick range.

Readers use manifest ranges to prune scans when `where` is provided. A rebuild path rescans Parquet files if a manifest is missing.

## Validation Against Core

- Source of truth: `crv.core.tables`.
- Enforced in strict mode:
  - Required/nullable sets and dtypes.
  - Safe scalar casts (`i64`, `f64`, `str`).
  - Shallow acceptance of `Struct` and `List[Struct]`.

## Public API

```python
import polars as pl
from crv.io import IoSettings, Dataset
from crv.core.grammar import TableName

# Configure the IO layer
settings = IoSettings(root_dir="out", tick_bucket_size=100)

# Bind to a specific run
ds = Dataset(settings, run_id="20250101-000000")

# Append a DataFrame
summary = ds.append(TableName.IDENTITY_EDGES, pl.DataFrame({...}))

# Lazy scan with pruning by tick range
lf = ds.scan(TableName.IDENTITY_EDGES, where={"tick_min": 0, "tick_max": 120})

# Eager read (optional limit)
df = ds.read(TableName.IDENTITY_EDGES, where={"tick_min": 0, "tick_max": 120}, limit=None)

# Inspect or rebuild a manifest
m = ds.manifest(TableName.IDENTITY_EDGES)
m2 = ds.rebuild_manifest(TableName.IDENTITY_EDGES)
```

## Quickstart

```python
import polars as pl
from crv.io import IoSettings, Dataset
from crv.core.grammar import TableName

# Configure where to write (default: "out")
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

## Configuration (IoSettings)

- `root_dir: str = "out"`
- `partitioning: Literal["tick_buckets"] = "tick_buckets"`
- `tick_bucket_size: int = 100`
- `row_group_size: int = 128 * 1024`
- `compression: Literal["zstd","lz4","snappy"] = "zstd"`
- `strict_schema: bool = True`
- `write_manifest_every_n: int = 1` (reserved for batching)
- `fs_protocol: str = "file"`, `fs_options: dict = {}` (future fsspec)

Config loading (env > TOML > defaults):

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

```bash
# Environment variables
export CRV_IO_ROOT_DIR="out"
export CRV_IO_TICK_BUCKET_SIZE="100"
export CRV_IO_ROW_GROUP_SIZE="131072"
export CRV_IO_COMPRESSION="zstd"          # zstd|lz4|snappy
export CRV_IO_FS_PROTOCOL="file"
export CRV_IO_STRICT_SCHEMA="1"           # 1/0/true/false/yes/no/on/off
export CRV_IO_WRITE_MANIFEST_EVERY_N="1"
```

## Run Bundle

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

## Testing

- Path/bucket math.
- Append atomicity & manifest updates.
- Scan pruning via manifest ranges.
- Manifest rebuild from FS.
- Strict schema enforcement.
- Import DAG isolation (no world/mind/lab/viz/app imports).

```bash
uv run ruff check .
uv run mypy --strict
uv run pytest -q
```

## Future Work

- Per‑bucket write locks for multi‑writer scenarios.
- fsspec remote storage (s3fs/gcsfs).
- Row‑level validation and deep struct validation.
- Streaming APIs (tail manifests).

## Contributing

- Align with `plans/io/io_module_starter_plan.md` and `plans/io/run_bundle_and_lab_integration_plan.md`.
- Respect the import DAG (no downstream imports).
