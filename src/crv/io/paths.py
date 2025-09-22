"""
Path and layout helpers for crv.io.

Overview (file protocol baseline)
- <root>/runs/<run_id>/tables/<table_name>/bucket=000123/part-<UUID>.parquet
- <root>/runs/<run_id>/tables/<table_name>/manifest.json

Source of truth
- Canonical table names: crv.core.grammar.TableName (lower_snake).
- Partitioning discipline: ["bucket"], with bucket computed in IO as tick // IoSettings.tick_bucket_size
  (defaults sourced from crv.core.constants).
- Schema/table descriptors: crv.core.tables (columns/dtypes/required/nullable).

Import DAG discipline
- stdlib + crv.io.config only. No imports from higher-level packages.

Notes
- This module focuses solely on path construction and run/table directory layout.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Final

from .config import IoSettings

_BUCKET_PREFIX: Final[str] = "bucket="
_MANIFEST_NAME: Final[str] = "manifest.json"


def bucket_id_for_tick(tick: int, bucket_size: int) -> int:
    """
    Compute the bucket id from a tick using floor division.

    Args:
        tick (int): Simulation tick (>= 0).
        bucket_size (int): Number of ticks per bucket (>= 1).

    Returns:
        int: Non-negative bucket id.

    Raises:
        ValueError: If bucket_size < 1 or tick < 0.
    """
    if bucket_size <= 0:
        raise ValueError("bucket_size must be >= 1")
    if tick < 0:
        raise ValueError("tick must be >= 0")
    return tick // bucket_size


def format_bucket_dir(bucket_id: int) -> str:
    """
    Format a bucket directory name as 'bucket=000123'.

    Args:
        bucket_id (int): Non-negative bucket id.

    Returns:
        str: Formatted directory name.

    Raises:
        ValueError: If bucket_id < 0.
    """
    if bucket_id < 0:
        raise ValueError("bucket_id must be >= 0")
    return f"{_BUCKET_PREFIX}{bucket_id:06d}"


def run_root(settings: IoSettings, run_id: str) -> str:
    """
    Root directory for a run.

    Args:
        settings (IoSettings): IO settings containing root_dir.
        run_id (str): Run identifier (see crv.core.ids.RunId; stored as string on disk).

    Returns:
        str: Path "<root>/runs/<run_id>".
    """
    return os.path.join(settings.root_dir, "runs", run_id)


def tables_root(settings: IoSettings, run_id: str) -> str:
    """
    Tables root for a run.

    Args:
        settings (IoSettings): IO settings.
        run_id (str): Run identifier.

    Returns:
        str: Path "<root>/runs/<run_id>/tables".
    """
    return os.path.join(run_root(settings, run_id), "tables")


def table_dir(settings: IoSettings, run_id: str, table_name: str) -> str:
    """
    Table directory path.

    Args:
        settings (IoSettings): IO settings.
        run_id (str): Run identifier.
        table_name (str): Canonical table name (lower_snake; see crv.core.grammar.TableName).

    Returns:
        str: Path "<root>/runs/<run_id>/tables/<table_name>".
    """
    return os.path.join(tables_root(settings, run_id), table_name)


def manifest_path(settings: IoSettings, run_id: str, table_name: str) -> str:
    """
    Path to table manifest.json.

    Args:
        settings (IoSettings): IO settings.
        run_id (str): Run identifier.
        table_name (str): Canonical table name.

    Returns:
        str: Path "<root>/runs/<run_id>/tables/<table_name>/manifest.json".
    """
    return os.path.join(table_dir(settings, run_id, table_name), _MANIFEST_NAME)


def bucket_dir(settings: IoSettings, run_id: str, table_name: str, bucket_id: int) -> str:
    """
    Bucket directory path.

    Args:
        settings (IoSettings): IO settings.
        run_id (str): Run identifier.
        table_name (str): Canonical table name.
        bucket_id (int): Non-negative bucket id.

    Returns:
        str: Path "<root>/runs/<run_id>/tables/<table_name>/bucket=000123".
    """
    return os.path.join(table_dir(settings, run_id, table_name), format_bucket_dir(bucket_id))


@dataclass(slots=True, frozen=True)
class PartPaths:
    """
    Container for a part's temporary and final file paths.

    Attributes:
        tmp_path (str): Temporary file path used for initial write (e.g., "*.parquet.tmp").
        final_path (str): Final file path after atomic rename (e.g., "*.parquet").
    """

    tmp_path: str
    final_path: str


def part_paths(
    settings: IoSettings, run_id: str, table_name: str, bucket_id: int, uuid_str: str
) -> PartPaths:
    """
    Compute temporary and final part file paths for a given bucket and UUID.

    Args:
        settings (IoSettings): IO settings.
        run_id (str): Run identifier.
        table_name (str): Canonical table name.
        bucket_id (int): Bucket id.
        uuid_str (str): Hex string used to build a unique part name.

    Returns:
        PartPaths: Paths for .parquet.tmp and final .parquet files.
    """
    base_dir = bucket_dir(settings, run_id, table_name, bucket_id)
    base_name = f"part-{uuid_str}.parquet"
    tmp_path = os.path.join(base_dir, base_name + ".tmp")
    final_path = os.path.join(base_dir, base_name)
    return PartPaths(tmp_path=tmp_path, final_path=final_path)


# -----------------------------------------------------------------------------
# Run ID helpers
# -----------------------------------------------------------------------------

# Allow common safe characters in run IDs: letters, digits, underscore, dash, dot, colon.
_RUN_ID_ALLOWED_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._:-]+$")


def validate_run_id(run_id: str) -> str:
    """
    Validate that a run_id is safe for filesystem paths.

    Args:
        run_id (str): Proposed run identifier.

    Returns:
        str: Same value if valid.

    Raises:
        ValueError: If run_id contains disallowed characters or is empty.
    """
    s = run_id or ""
    if not s or not _RUN_ID_ALLOWED_RE.match(s):
        raise ValueError("run_id contains illegal characters; allowed pattern is [A-Za-z0-9._:-]+")
    return s


def normalize_run_id(run_id: str) -> str:
    """
    Normalize a free-form run id by trimming and replacing spaces with underscores,
    then validate against the allowed character set.

    Args:
        run_id (str): Candidate run identifier.

    Returns:
        str: Normalized and validated run id.

    Raises:
        ValueError: If the normalized run_id remains invalid.
    """
    s = (run_id or "").strip().replace(" ", "_")
    return validate_run_id(s)
