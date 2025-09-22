"""
Per-table manifest data structures and helpers.

Manifest layout (JSON at <table_dir>/manifest.json):
{
  "table": "<table_name>",
  "version": 1,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "partitions": {
    "000123": {
      "bucket_id": 123,
      "state": "ready",
      "tick_min": 0,
      "tick_max": 199,
      "row_count": 12345,
      "byte_size": 987654,
      "parts": [
        {
          "path": "part-<UUID>.parquet",
          "rows": 123,
          "bytes": 4567,
          "tick_min": 0,
          "tick_max": 12,
          "created_at": "ISO-8601"
        }
      ]
    }
  }
}

Notes:
- Part path is stored relative to the bucket directory to keep the manifest relocatable.
- Partition key is zero-padded "000123" (same format as bucket=000123).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from .config import IoSettings
from .fs import makedirs, open_write, rename_atomic
from .paths import bucket_dir, manifest_path

State = Literal["writing", "ready"]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class PartMeta:
    """
    Per-part metadata recorded in the table manifest.

    Attributes:
        path (str): Relative file name under the bucket directory
            (e.g., "part-<UUID>.parquet").
        rows (int): Row count for this part.
        bytes (int): File size in bytes for this part.
        tick_min (int): Minimum tick present in this part.
        tick_max (int): Maximum tick present in this part.
        created_at (str): ISO-8601 timestamp indicating when the part was written.
    """

    path: str  # relative to bucket_dir
    rows: int
    bytes: int
    tick_min: int
    tick_max: int
    created_at: str


@dataclass(slots=True)
class PartitionMeta:
    """
    Aggregated metadata for a single partition (bucket).

    Attributes:
        bucket_id (int): Numeric bucket identifier (e.g., 123).
        state (State): Partition state, typically "ready" after a successful append.
        tick_min (int): Minimum tick across all parts in this bucket.
        tick_max (int): Maximum tick across all parts in this bucket.
        row_count (int): Total number of rows across parts in this bucket.
        byte_size (int): Total bytes across parts in this bucket.
        parts (list[PartMeta]): Ordered list of part metadata objects.
    """

    bucket_id: int
    state: State
    tick_min: int
    tick_max: int
    row_count: int
    byte_size: int
    parts: list[PartMeta] = field(default_factory=list)


@dataclass(slots=True)
class TableManifest:
    """
    Manifest model persisted at <table_dir>/manifest.json.

    Attributes:
        table (str): Canonical table name (lower_snake).
        version (int): Manifest schema version (independent of core SCHEMA_V).
        created_at (str): ISO-8601 creation timestamp.
        updated_at (str): ISO-8601 timestamp of the last update.
        partitions (dict[str, PartitionMeta]): Mapping of zero-padded bucket key
            (e.g., "000123") to PartitionMeta.

    Notes:
        - Part paths are stored relative to the bucket directory to keep the manifest
          relocatable.
        - Partition keys are zero-padded to 6 digits (e.g., "000123").
    """

    table: str
    version: int
    created_at: str
    updated_at: str
    partitions: dict[str, PartitionMeta]

    def to_json_obj(self) -> dict[str, Any]:
        def encode(obj: Any) -> Any:
            if isinstance(obj, PartitionMeta):
                d = asdict(obj)
                d["parts"] = [asdict(p) for p in obj.parts]
                return d
            if isinstance(obj, PartMeta):
                return asdict(obj)
            return obj

        return {
            "table": self.table,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "partitions": {k: encode(v) for k, v in self.partitions.items()},
        }

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> TableManifest:
        partitions: dict[str, PartitionMeta] = {}
        for key, p in (obj.get("partitions") or {}).items():
            parts = [PartMeta(**pm) for pm in (p.get("parts") or [])]
            partitions[key] = PartitionMeta(
                bucket_id=int(p["bucket_id"]),
                state=p["state"],
                tick_min=int(p["tick_min"]),
                tick_max=int(p["tick_max"]),
                row_count=int(p["row_count"]),
                byte_size=int(p["byte_size"]),
                parts=parts,
            )
        return cls(
            table=obj["table"],
            version=int(obj.get("version", 1)),
            created_at=obj.get("created_at") or _utc_now_iso(),
            updated_at=obj.get("updated_at") or _utc_now_iso(),
            partitions=partitions,
        )


# -----------------------------------------------------------------------------
# File I/O
# -----------------------------------------------------------------------------


def load_manifest(settings: IoSettings, run_id: str, table_name: str) -> TableManifest | None:
    """
    Load a table's manifest.json if present.

    Args:
        settings: IoSettings used to resolve layout/root directory.
        run_id (str): Run identifier (stored as string on disk).
        table_name (str): Canonical table name (lower_snake).

    Returns:
        TableManifest | None: Parsed manifest model, or None if not found.

    Notes:
        - This function does not validate against core descriptors; it simply loads
          the persisted manifest metadata for pruning/inspection.
    """
    mpath = manifest_path(settings, run_id, table_name)
    if not os.path.exists(mpath):
        return None
    with open(mpath, encoding="utf-8") as fh:
        data = json.load(fh)
    return TableManifest.from_json_obj(data)


def write_manifest(
    settings: IoSettings, run_id: str, table_name: str, manifest: TableManifest
) -> None:
    """
    Persist manifest.json atomically.

    The write path is: serialize JSON → write to "<final>.tmp" → close/flush →
    atomic rename to final path using os.replace (same filesystem).

    Args:
        settings: IoSettings for layout.
        run_id (str): Run identifier.
        table_name (str): Canonical table name.
        manifest (TableManifest): Manifest model to serialize.

    Raises:
        OSError: If filesystem operations fail (caller may wrap in IoManifestError).

    Notes:
        - Ensures directory exists prior to writing.
        - Keeps the manifest relocatable by using relative part paths.
    """
    tdir = os.path.dirname(manifest_path(settings, run_id, table_name))
    makedirs(tdir, exist_ok=True)
    final_path = manifest_path(settings, run_id, table_name)
    tmp_path = final_path + ".tmp"
    payload = json.dumps(manifest.to_json_obj(), indent=2, sort_keys=False).encode("utf-8")
    with open_write(tmp_path) as fh:
        fh.write(payload)
        # fsync is handled by open_write/close; os.replace is atomic on same FS
    rename_atomic(tmp_path, final_path)


# -----------------------------------------------------------------------------
# Update helpers
# -----------------------------------------------------------------------------


def _bucket_key(bucket_id: int) -> str:
    return f"{bucket_id:06d}"


def update_with_new_part(
    manifest: TableManifest,
    bucket_id: int,
    part_meta: PartMeta,
) -> None:
    """
    Update the manifest with a newly written part for the given bucket.

    Args:
        manifest (TableManifest): Manifest instance to mutate.
        bucket_id (int): Numeric bucket id (e.g., 123).
        part_meta (PartMeta): Metadata of the newly written parquet part.

    Notes:
        - Creates a new PartitionMeta if the bucket is not yet present.
        - Updates per-bucket aggregates (tick range, row/byte totals).
        - Sets partition state to "ready" under single-writer semantics.
    """
    key = _bucket_key(bucket_id)
    pm = manifest.partitions.get(key)
    if pm is None:
        pm = PartitionMeta(
            bucket_id=bucket_id,
            state="writing",
            tick_min=part_meta.tick_min,
            tick_max=part_meta.tick_max,
            row_count=part_meta.rows,
            byte_size=part_meta.bytes,
            parts=[part_meta],
        )
        manifest.partitions[key] = pm
    else:
        pm.parts.append(part_meta)
        pm.tick_min = min(pm.tick_min, part_meta.tick_min)
        pm.tick_max = max(pm.tick_max, part_meta.tick_max)
        pm.row_count += part_meta.rows
        pm.byte_size += part_meta.bytes
        pm.state = "writing"
    manifest.updated_at = _utc_now_iso()
    # finalize state as ready for single-writer semantics
    pm.state = "ready"


def new_manifest(table_name: str, version: int = 1) -> TableManifest:
    """
    Create a fresh TableManifest with no partitions.

    Args:
        table_name (str): Canonical table name (lower_snake).
        version (int): Manifest schema version (default: 1).

    Returns:
        TableManifest: Newly created manifest with timestamps set to now.
    """
    now = _utc_now_iso()
    return TableManifest(
        table=table_name,
        version=version,
        created_at=now,
        updated_at=now,
        partitions={},
    )


# -----------------------------------------------------------------------------
# Rebuild (FS walk + lightweight statistics)
# -----------------------------------------------------------------------------


def rebuild_manifest_from_fs(settings: IoSettings, run_id: str, table_name: str) -> TableManifest:
    """
    Rebuild a manifest by walking the table directory and scanning each part
    to compute rows and tick ranges. This is a slower, best-effort operation
    intended for recovery or validation.

    Requires polars. We import it lazily to avoid import overhead elsewhere.
    """
    import polars as pl  # lazy import

    m = new_manifest(table_name)
    # Walk buckets
    tdir = os.path.dirname(manifest_path(settings, run_id, table_name))
    # table_dir = <root>/runs/<run_id>/tables/<table_name>
    table_dir = tdir
    # buckets under table_dir
    try:
        bucket_names = os.listdir(table_dir)
    except FileNotFoundError:
        bucket_names = []
    for name in sorted(bucket_names):
        if not name.startswith("bucket="):
            continue
        try:
            bucket_id = int(name.split("=", 1)[1])
        except Exception:
            continue
        bdir = bucket_dir(settings, run_id, table_name, bucket_id)
        try:
            files = os.listdir(bdir)
        except FileNotFoundError:
            files = []
        for fn in sorted(files):
            if not fn.endswith(".parquet"):
                continue
            fpath = os.path.join(bdir, fn)
            # Collect stats via a tiny scan
            lf = pl.scan_parquet(fpath)
            stats = lf.select(
                [
                    pl.min("tick").alias("min_tick"),
                    pl.max("tick").alias("max_tick"),
                    pl.len().alias("n"),
                ]
            ).collect()
            tick_min = int(stats["min_tick"][0]) if stats.height else 0
            tick_max = int(stats["max_tick"][0]) if stats.height else 0
            rows = int(stats["n"][0]) if stats.height else 0
            bytes_ = int(os.path.getsize(fpath)) if os.path.exists(fpath) else 0
            part = PartMeta(
                path=fn,
                rows=rows,
                bytes=bytes_,
                tick_min=tick_min,
                tick_max=tick_max,
                created_at=_utc_now_iso(),
            )
            update_with_new_part(m, bucket_id, part)
    return m
