"""
Read utilities for canonical CRV tables.

Overview
- scan(): Returns a Polars LazyFrame with optional manifest-based pruning.
- read(): Collects a DataFrame from scan(), with an optional pre-collect row cap.

Source of truth
- Canonical table names come from crv.core.grammar.TableName.
- Table descriptors (columns/dtypes/required/nullable/partitioning) come from crv.core.tables.
- Schema models and combination rules live in crv.core.schema; this module performs no schema normalization.
- Version metadata (SCHEMA_V) comes from crv.core.versioning.

Pruning semantics
- If a table manifest exists, partition (bucket) pruning uses tick_min/tick_max overlap checks.
- Regardless of pruning, when a filter is provided, we apply explicit row-level tick filters
  to ensure correctness even if files slightly over-cover the range.
- If no manifest is present, we fall back to an FS walk to discover parts.

Import DAG discipline
- Depends on stdlib, polars, and crv.io helpers; does not import higher layers (world/mind/lab/viz/app).

Notes
- File protocol baseline; remote backends (e.g., fsspec) can be layered later.
"""

from __future__ import annotations

import os
from typing import Any

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId

from .config import IoSettings
from .errors import IoManifestError
from .fs import listdir, walk_parquet_files
from .manifest import TableManifest, load_manifest
from .paths import bucket_dir, table_dir


def _normalize_table_name(table: TableName | str) -> str:
    return table.value if isinstance(table, TableName) else str(table)


def _paths_from_manifest(
    settings: IoSettings,
    run_id: str,
    tname: str,
    manifest: TableManifest,
    where: dict[str, Any] | None,
) -> list[str]:
    # Compute candidate bucket ids based on tick overlap, if provided.
    tick_min = None
    tick_max = None
    if where:
        tick_min = where.get("tick_min")
        tick_max = where.get("tick_max")
    selected: list[str] = []
    for key, pmeta in manifest.partitions.items():
        # If no filter, include all.
        include = True
        if tick_min is not None or tick_max is not None:
            # Overlap test with partition tick range
            # Interpret None as open-ended.
            lo = pmeta.tick_min
            hi = pmeta.tick_max
            # If tick_min is specified, require hi >= tick_min.
            if tick_min is not None and hi < int(tick_min):
                include = False
            # If tick_max is specified, require lo <= tick_max.
            if tick_max is not None and lo > int(tick_max):
                include = False
        if not include:
            continue
        bdir = bucket_dir(settings, run_id, tname, pmeta.bucket_id)
        for part in pmeta.parts:
            selected.append(os.path.join(bdir, part.path))
    return selected


# TODO: Determine if we want to keep this fallback function or not. Remove if not needed.
def _paths_from_fs_walk(settings: IoSettings, run_id: str, tname: str) -> list[str]:
    # Fallback: walk the table directory for parquet files.
    tdir = table_dir(settings, run_id, tname)
    # Optimize a little: only descend into bucket= subdirs if present.
    out: list[str] = []
    for name in sorted(list(map(os.path.basename, listdir(tdir)))):
        if name.startswith("bucket="):
            try:
                bucket_id = int(name.split("=", 1)[1])
            except Exception:
                continue
            bdir = os.path.join(tdir, name)
            for fn in sorted(os.listdir(bdir)):
                if fn.endswith(".parquet"):
                    out.append(os.path.join(bdir, fn))
        else:
            # Non-standard layout; allow any parquet found at top-level (defensive).
            p = os.path.join(tdir, name)
            if p.endswith(".parquet"):
                out.append(p)
    if not out and os.path.isdir(tdir):
        # As a last resort, do a full recursive walk.
        out = sorted(walk_parquet_files(tdir))
    return out


def scan(
    settings: IoSettings,
    run_id: RunId,
    table: TableName | str,
    where: dict[str, Any] | None = None,
) -> pl.LazyFrame:
    """
    Create a LazyFrame scanning selected parts, with optional manifest-based pruning.

    Args:
        settings (IoSettings): IO configuration used to resolve paths/layout.
        run_id (RunId): Run identifier (see crv.core.ids.RunId; stored as string on disk).
        table (TableName | str): Canonical table name (enum or lower_snake string).
        where (dict[str, Any] | None): Optional tick filter with keys:
            - "tick_min": int | None
            - "tick_max": int | None

    Returns:
        pl.LazyFrame: Lazy scan over discovered parts. When a manifest exists, partitions
        (buckets) are pruned using tick range overlap; explicit row-level filters on "tick"
        are applied to guarantee correctness even after pruning.

    Notes:
        - When no manifest is present, we conservatively include all *.parquet files found
          via a directory walk under the table directory.
        - Callers should rely on crv.core.tables descriptors for schema/dtype expectations.
    """
    tname = _normalize_table_name(table)
    manifest = load_manifest(settings, run_id, tname)
    if manifest is None:
        raise IoManifestError(
            f"manifest missing for table {tname!r} in run {run_id!r}; call Dataset.rebuild_manifest()"
        )
    paths = _paths_from_manifest(settings, run_id, tname, manifest, where)

    if not paths:
        # Return an empty scan via a dummy empty dataframe to keep types simple.
        # Consumers can handle empty results.
        return pl.LazyFrame()

    lf = pl.scan_parquet(paths)

    # Apply row-level tick filter if provided
    if where:
        tick_min = where.get("tick_min")
        tick_max = where.get("tick_max")
        if tick_min is not None:
            lf = lf.filter(pl.col("tick") >= int(tick_min))
        if tick_max is not None:
            lf = lf.filter(pl.col("tick") <= int(tick_max))

    return lf


def read(
    settings: IoSettings,
    run_id: RunId,
    table: TableName | str,
    where: dict[str, Any] | None = None,
    limit: int | None = None,
) -> pl.DataFrame:
    """
    Collect a DataFrame from scan(), optionally applying a pre-collect row cap.

    Args:
        settings (IoSettings): IO configuration used to resolve paths/layout.
        run_id (RunId): Run identifier (see crv.core.ids.RunId; stored as string on disk).
        table (TableName | str): Canonical table name (enum or lower_snake string).
        where (dict[str, Any] | None): Optional {"tick_min","tick_max"} filter.
        limit (int | None): Optional row cap applied before collect().

    Returns:
        pl.DataFrame: Materialized frame (possibly empty).

    Notes:
        - Equivalent to scan(...).limit(limit).collect() when limit is provided.
        - Schema/dtype contracts are defined in crv.core.tables; this function does not
          perform validation or casting (that occurs on write).
    """
    lf = scan(settings, run_id, table, where=where)
    if limit is not None:
        lf = lf.limit(int(limit))
    return lf.collect()
