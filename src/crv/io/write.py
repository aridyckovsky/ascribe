"""
Append-only writer for canonical CRV tables.

Overview
- Computes/ensures tick-bucket partitioning (bucket = tick // IoSettings.tick_bucket_size).
- Validates frames against crv.core.tables descriptors (source of truth).
- Writes Parquet parts with atomic tmp → ready rename and embeds version/table/run_id metadata.
- Updates per-table manifest.json with per-part and per-bucket aggregates.

Source of truth
- Canonical table names: crv.core.grammar.TableName (lower_snake).
- Table descriptors and partitioning discipline: crv.core.tables (partitioning=["bucket"]).
- Schema version metadata: crv.core.versioning.SCHEMA_V (embedded in Parquet key-value metadata).
- Domain errors (naming/combination rules): crv.core.schema / crv.core.errors.
- IO-layer errors: crv.io.errors.IoSchemaError, IoWriteError, IoManifestError.

Notes
- Single-writer semantics initially (no inter-process locking).
- File protocol baseline; remote backends (e.g., fsspec) can be layered later.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import polars as pl
import pyarrow.parquet as pq

from crv.core.grammar import TableName
from crv.core.tables import get_table
from crv.core.versioning import SCHEMA_V

from .config import IoSettings
from .errors import IoManifestError, IoSchemaError, IoWriteError
from .fs import fsync_path, makedirs, rename_atomic
from .manifest import PartMeta, load_manifest, new_manifest, update_with_new_part, write_manifest
from .paths import bucket_dir, part_paths
from .validate import validate_frame_against_descriptor


def _now_iso() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(UTC).isoformat()


def _require_tick_column(df: pl.DataFrame) -> None:
    """
    Ensure the presence of the 'tick' column required for bucket computation.

    Raises:
        IoSchemaError: If 'tick' column is missing.
    """
    if "tick" not in df.columns:
        raise IoSchemaError("column 'tick' is required to compute bucket partitioning")


def _ensure_bucket_column(df: pl.DataFrame, bucket_size: int) -> pl.DataFrame:
    """
    Compute and attach the 'bucket' column as tick // bucket_size (Int64).

    Notes:
        Always recomputed to ensure consistency with IoSettings.tick_bucket_size.
    """
    return df.with_columns((pl.col("tick") // bucket_size).cast(pl.Int64).alias("bucket"))


def _split_by_bucket(df: pl.DataFrame) -> dict[int, pl.DataFrame]:
    """
    Split a DataFrame into a dict of bucket_id -> subframe.

    Returns:
        dict[int, pl.DataFrame]: Mapping from bucket id to filtered subframe.
    """
    buckets = df.get_column("bucket").cast(pl.Int64).unique().sort().to_list()
    out: dict[int, pl.DataFrame] = {}
    for b in buckets:
        bi = int(b)
        out[bi] = df.filter(pl.col("bucket") == bi)
    return out


def _tick_stats(df: pl.DataFrame) -> tuple[int, int, int]:
    """
    Compute minimal statistics over 'tick' for a subframe.

    Returns:
        tuple[int, int, int]: (tick_min, tick_max, row_count)
    """
    if df.is_empty():
        return 0, 0, 0
    stats = df.select(
        [
            pl.min("tick").alias("min_tick"),
            pl.max("tick").alias("max_tick"),
            pl.len().alias("n"),
        ]
    )
    return int(stats["min_tick"][0]), int(stats["max_tick"][0]), int(stats["n"][0])


def append(
    settings: IoSettings,
    run_id: str,
    table: TableName | str,
    df: pl.DataFrame,
    *,
    validate_schema: bool = True,
    validate_rows: bool = False,  # placeholder for future row-level checks
) -> dict[str, Any]:
    """
    Append a DataFrame to a canonical table with atomic semantics.

    Args:
        settings (IoSettings): IO configuration (root_dir, compression, etc.).
        run_id (str): Run identifier used to construct dataset paths
            (see crv.core.ids.RunId; stored as string on disk).
        table (TableName | str): Canonical table name (enum or lower_snake string).
        df (pl.DataFrame): Polars DataFrame to append. Must include 'tick'; 'bucket'
            is computed as tick // IoSettings.tick_bucket_size.
        validate_schema (bool): Validate against crv.core.tables descriptor (default True).
        validate_rows (bool): Reserved for future row-level validation (unused).

    Returns:
        dict[str, Any]: Summary with keys:
            - table (str)
            - run_id (str)
            - parts (list[dict]): Per-part {"bucket_id","path","rows","bytes","tick_min","tick_max"}
            - rows (int): Total rows written
            - buckets (list[int]): Buckets touched

    Raises:
        IoSchemaError: Frame failed validation against core descriptor.
        IoWriteError: Parquet write/fsync/atomic-rename failed.
        IoManifestError: Manifest write failed.

    Notes:
        - Parquet parts embed metadata:
            b"crv_schema_version" = f"{SCHEMA_V.major}.{SCHEMA_V.minor}@{SCHEMA_V.date}"
            b"crv_table_name"     = tname
            b"crv_run_id"         = run_id
        - Single-writer semantics initially; no inter-process locking.
    """
    tname = table.value if isinstance(table, TableName) else str(table)
    desc = get_table(TableName(tname))

    if df.is_empty():
        # No-op append returns empty summary
        return {"table": tname, "run_id": run_id, "parts": [], "rows": 0, "buckets": []}

    _require_tick_column(df)

    # Ensure/compute bucket column
    df = _ensure_bucket_column(df, settings.tick_bucket_size)

    # Validate schema and cast scalars as needed
    if validate_schema:
        df = validate_frame_against_descriptor(df, desc, strict=settings.strict_schema)

    # Split by bucket and write each part atomically
    parts_summary: list[dict[str, Any]] = []
    total_rows = 0
    by_bucket = _split_by_bucket(df)

    # Load or create manifest
    manifest = load_manifest(settings, run_id, tname)
    if manifest is None:
        manifest = new_manifest(tname)

    for bucket_id, df_b in by_bucket.items():
        # Directory prep
        bdir = bucket_dir(settings, run_id, tname, bucket_id)
        makedirs(bdir, exist_ok=True)

        # Part paths
        uid = uuid.uuid4().hex
        ppaths = part_paths(settings, run_id, tname, bucket_id, uid)

        # Write parquet to tmp, fsync, then rename atomically
        try:
            # Write parquet via pyarrow to embed key-value metadata (schema version, table, run_id).
            # Convert Polars DataFrame to Arrow Table.
            arrow_table = df_b.to_arrow()
            # Prepare metadata (keys/values must be bytes).
            meta = dict(arrow_table.schema.metadata or {})
            meta.update(
                {
                    b"crv_schema_version": f"{SCHEMA_V.major}.{SCHEMA_V.minor}@{SCHEMA_V.date}".encode(),
                    b"crv_table_name": tname.encode("utf-8"),
                    b"crv_run_id": run_id.encode("utf-8"),
                }
            )
            arrow_table = arrow_table.replace_schema_metadata(meta)
            # Write with compression and row group size.
            pq.write_table(
                arrow_table,
                ppaths.tmp_path,
                compression=settings.compression,
                row_group_size=settings.row_group_size,
            )
            fsync_path(ppaths.tmp_path)
            rename_atomic(ppaths.tmp_path, ppaths.final_path)
        except Exception as exc:
            # Best effort cleanup of tmp file
            try:
                if os.path.exists(ppaths.tmp_path):
                    os.remove(ppaths.tmp_path)
            except Exception:
                pass
            raise IoWriteError(
                f"failed to write parquet part for bucket {bucket_id}: {exc}"
            ) from exc

        # Stats for manifest and summary
        tmin, tmax, nrows = _tick_stats(df_b)
        total_rows += nrows
        nbytes = int(os.path.getsize(ppaths.final_path)) if os.path.exists(ppaths.final_path) else 0

        # Update manifest (store path relative to bucket dir)
        rel_name = os.path.basename(ppaths.final_path)
        part_meta = PartMeta(
            path=rel_name,
            rows=nrows,
            bytes=nbytes,
            tick_min=tmin,
            tick_max=tmax,
            created_at=_now_iso(),
        )
        update_with_new_part(manifest, bucket_id, part_meta)

        parts_summary.append(
            {
                "bucket_id": bucket_id,
                "path": ppaths.final_path,
                "rows": nrows,
                "bytes": nbytes,
                "tick_min": tmin,
                "tick_max": tmax,
            }
        )

    # Persist manifest atomically
    try:
        write_manifest(settings, run_id, tname, manifest)
    except Exception as exc:
        raise IoManifestError(f"failed to write manifest for table {tname!r}: {exc}") from exc

    return {
        "table": tname,
        "run_id": run_id,
        "parts": parts_summary,
        "rows": total_rows,
        "buckets": sorted(by_bucket.keys()),
    }
