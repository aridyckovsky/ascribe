"""
Artifacts helpers for Run Bundle outputs (lab, world, mind).

Layout (file protocol baseline)
- <root>/runs/<run_id>/artifacts/lab/tidy/*.parquet
- <root>/runs/<run_id>/artifacts/lab/probes/*.parquet
- <root>/runs/<run_id>/artifacts/lab/policy/*.parquet
- <root>/runs/<run_id>/artifacts/lab/audit/*.(json|parquet)

Notes
- This module provides stdlib-only path/atomic write helpers for artifacts.
- Parquet writing uses Polars if available (imported inside functions).
- Atomicity: tmp write -> fsync -> os.replace (same FS) using io.fs helpers.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import polars as pl  # type: ignore

from crv.core.ids import RunId

from .config import IoSettings
from .fs import fsync_path, makedirs, open_write, rename_atomic
from .paths import run_root

_LAB_SUBDIR = ("tidy", "probes", "policy", "audit")


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def artifacts_root(settings: IoSettings, run_id: RunId) -> str:
    """
    Root directory for run artifacts.

    Returns:
        str: "<root>/runs/<run_id>/artifacts"
    """
    return os.path.join(run_root(settings, str(run_id)), "artifacts")


def lab_dir(
    settings: IoSettings, run_id: RunId, subdir: Literal["tidy", "policy", "probes", "audit"]
) -> str:
    """
    Subdirectory path for lab artifacts.

    Args:
        subdir: One of {"tidy","policy","probes","audit"}.

    Returns:
        str: "<root>/runs/<run_id>/artifacts/lab/<subdir>"
    """
    if subdir not in _LAB_SUBDIR:
        raise ValueError(f"unknown lab artifacts subdir {subdir!r}")
    p = os.path.join(artifacts_root(settings, run_id), "lab", subdir)
    makedirs(p, exist_ok=True)
    return p


def file_stat(path: str) -> dict[str, Any]:
    """
    Return basic file stats.

    Returns:
        dict: {"path": path, "bytes": int, "created_at": ISO8601}
    """
    return {
        "path": path,
        "bytes": int(os.path.getsize(path)) if os.path.exists(path) else 0,
        "created_at": _utc_now_iso(),
    }


def write_text_atomic(path: str, text: str) -> dict[str, Any]:
    """
    Atomically write a small text/JSON payload.

    Args:
        path: Final destination path.
        text: UTF-8 text.

    Returns:
        dict: file_stat(path) + {"wrote_text": True}
    """
    makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    payload = text.encode("utf-8")
    with open_write(tmp) as fh:
        fh.write(payload)
    rename_atomic(tmp, path)
    st = file_stat(path)
    st["wrote_text"] = True
    return st


def write_parquet_atomic(path: str, df: pl.DataFrame) -> dict[str, Any]:
    """
    Atomically write a Polars DataFrame to parquet with reasonable defaults.

    Args:
        path: Final parquet path.
        df: Polars DataFrame (pl.DataFrame). Imported lazily to avoid module-level dependency.

    Returns:
        dict: file_stat(path) + {"rows": int}
    """
    try:
        import polars as pl  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("polars is required to write parquet artifacts") from e

    if not isinstance(df, pl.DataFrame):
        raise TypeError("write_parquet_atomic expects a polars.DataFrame")

    makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    # Use polars defaults for artifacts; canonical tables use crv.io.write settings
    df.write_parquet(tmp)
    # Ensure bytes hit disk before rename
    fsync_path(tmp)
    rename_atomic(tmp, path)
    st = file_stat(path)
    st["rows"] = int(df.height)
    return st
