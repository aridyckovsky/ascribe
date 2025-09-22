"""
Dataset facade for crv.io.

Provides a convenient object to operate on a specific run (run_id) with
append/scan/read/manifest/rebuild_manifest helpers. The IO layer is Polars/Arrow‑first
and treats crv.core as the single source of truth for canonical table names,
descriptors (columns/dtypes/required/nullable/partitioning), and schema versioning.

Source of truth
- Table names: crv.core.grammar.TableName
- Descriptors: crv.core.tables (partitioning=[ "bucket" ], version=SCHEMA_V)
- IDs: crv.core.ids (RunId)
- Schema models/combination rules: crv.core.schema
- Versioning metadata: crv.core.versioning.SCHEMA_V

Import DAG discipline:
- Depends only on stdlib, polars/pyarrow, and crv.core.* (via read/write/manifest modules).
- Must not import higher layers (world, mind, lab, viz, app).
"""

from __future__ import annotations

from typing import Any

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId

from .config import IoSettings
from .manifest import TableManifest, load_manifest, rebuild_manifest_from_fs, write_manifest
from .read import read as _read
from .read import scan as _scan
from .write import append as _append


class Dataset:
    """
    Facade bound to a specific IoSettings and run_id.

    Notes:
        - run_id should be produced by crv.core.ids.make_run_id (type: RunId). It is
          stored as a string on disk; the NewType is used for clarity and static checks.
        - All schema/dtype decisions are delegated to crv.core.tables; this class does
          not redefine schema contracts.
        - Writes are append‑only and atomic (tmp → ready rename) per part; manifests
          are updated per append and can be rebuilt from the filesystem if needed.
    """

    def __init__(self, settings: IoSettings, run_id: RunId) -> None:
        """
        Initialize a dataset facade bound to a specific run.

        Args:
            settings (IoSettings): IO configuration (root_dir, compression, etc.).
            run_id (RunId): Run identifier used to construct on‑disk paths.

        Notes:
            This does not perform any I/O at construction time.
        """
        self.settings = settings
        self.run_id = run_id

    # ---------------------------------------------------------------------
    # Write
    # ---------------------------------------------------------------------
    def append(
        self,
        table: TableName | str,
        df: pl.DataFrame,
        *,
        validate_schema: bool = True,
        validate_rows: bool = False,
    ) -> dict[str, Any]:
        """
        Append a Polars DataFrame to a canonical table with atomic semantics.

        Args:
            table (TableName | str): Canonical table name (enum or lower_snake string).
            df (pl.DataFrame): Frame to append. Must include tick; bucket is computed
                as tick // IoSettings.tick_bucket_size.
            validate_schema (bool): Validate frame against crv.core.tables descriptor.
            validate_rows (bool): Reserved for future row‑level validation (unused).

        Returns:
            dict[str, Any]: Summary including:
                - table (str)
                - run_id (str)
                - parts (list[dict]): Per‑part {"bucket_id","path","rows","bytes","tick_min","tick_max"}
                - rows (int): Total rows written
                - buckets (list[int]): Buckets touched

        Raises:
            crv.io.errors.IoSchemaError: Schema validation failed vs core descriptor.
            crv.io.errors.IoWriteError: Parquet write/rename failed.
            crv.io.errors.IoManifestError: Manifest write failed.

        Notes:
            - Parquet parts embed crv.core.versioning.SCHEMA_V and table/run_id metadata.
            - Single‑writer semantics initially; no inter‑process locking.
        """
        return _append(
            self.settings,
            self.run_id,
            table,
            df,
            validate_schema=validate_schema,
            validate_rows=validate_rows,
        )

    # ---------------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------------
    def scan(self, table: TableName | str, where: dict[str, Any] | None = None) -> pl.LazyFrame:
        """
        Return a Polars LazyFrame pruned by manifest when available.

        Args:
            table (TableName | str): Canonical table name.
            where (dict | None): Optional tick range filter:
                {"tick_min": int | None, "tick_max": int | None}.

        Returns:
            pl.LazyFrame: A lazy scan over selected parts. If a manifest is present,
            partition (bucket) pruning is applied. Row‑level tick filters are applied
            explicitly to ensure correctness even after pruning.
        """
        return _scan(self.settings, self.run_id, table, where=where)

    def read(
        self,
        table: TableName | str,
        where: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame:
        """
        Collect a DataFrame from scan(), optionally applying a pre‑collect row cap.

        Args:
            table (TableName | str): Canonical table name.
            where (dict | None): Optional {"tick_min","tick_max"} filter.
            limit (int | None): Optional row cap applied before collect().

        Returns:
            pl.DataFrame: Materialized frame (possibly empty).
        """
        return _read(self.settings, self.run_id, table, where=where, limit=limit)

    # ---------------------------------------------------------------------
    # Manifest
    # ---------------------------------------------------------------------
    def manifest(self, table: TableName | str) -> TableManifest | None:
        """
        Load the per‑table manifest if present.

        Args:
            table (TableName | str): Canonical table name.

        Returns:
            TableManifest | None: The manifest model if found; otherwise None.
        """
        tname = table.value if isinstance(table, TableName) else str(table)
        return load_manifest(self.settings, self.run_id, tname)

    def rebuild_manifest(self, table: TableName | str) -> TableManifest:
        """
        Rebuild the manifest by scanning parquet files under the table directory,
        recomputing per‑part stats (rows, bytes, tick_min, tick_max), and writing
        the manifest atomically.

        Args:
            table (TableName | str): Canonical table name.

        Returns:
            TableManifest: Newly built manifest.

        Notes:
            This is a slower, best‑effort recovery/validation path (lazy Polars scans).
        """
        tname = table.value if isinstance(table, TableName) else str(table)
        m = rebuild_manifest_from_fs(self.settings, self.run_id, tname)
        write_manifest(self.settings, self.run_id, tname, m)
        return m
