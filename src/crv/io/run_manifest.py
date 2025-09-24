"""
Run-bundle manifest writer and indexers for canonical tables and artifacts.

Layout (file protocol baseline)
- <root>/runs/<run_id>/bundle.manifest.json
- <root>/runs/<run_id>/tables/<table_name>/manifest.json
- <root>/runs/<run_id>/artifacts/lab/{tidy,probes,policy,audit}/*

Notes
- This module depends only on stdlib and crv.core.* (for SCHEMA_V) plus local io helpers.
- It does NOT read parquet files for canonical table stats; it only reads per-table manifests.
- For artifacts, it best-effort collects file sizes and optionally row counts if Polars is importable.
+
+Tables Index Schema (bundle.manifest["tables"]):
+- "<table_name>": {
+    rows: int,
+    bytes: int,
+    total_rows: int,    # canonical alias of rows
+    total_bytes: int,   # canonical alias of bytes
+    tick_min: int | null,
+    tick_max: int | null,
+    buckets: list[int]
+  }
+"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from crv.core.ids import RunId  # typing clarity only
from crv.core.versioning import SCHEMA_V

from .config import IoSettings
from .fs import makedirs, open_write, rename_atomic
from .manifest import load_manifest
from .paths import run_root, tables_root


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def bundle_manifest_path(settings: IoSettings, run_id: RunId) -> str:
    """
    Path to the run-bundle manifest file.

    Returns:
        str: "<root>/runs/<run_id>/bundle.manifest.json"
    """
    return os.path.join(run_root(settings, str(run_id)), "bundle.manifest.json")


def _safe_pkg_version(mod_name: str) -> str | None:
    try:
        mod = __import__(mod_name)
        # Prefer __version__ attribute; for pyarrow it's pyarrow.__version__
        return getattr(mod, "__version__", None)
    except Exception:
        return None


def _git_info() -> dict[str, Any]:
    """
    Best-effort git metadata for reproducibility. Returns nulls on failure.
    """
    sha: str | None = None
    dirty: bool | None = None
    try:
        # Resolve current HEAD sha
        r = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
        sha = (r.stdout or "").strip() or None
        # Check dirty status
        r2 = subprocess.run(
            ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
        )
        s = (r2.stdout or "").strip()
        dirty = bool(s) if sha is not None else None
    except Exception:
        sha = None
        dirty = None
    return {"sha": sha, "dirty": dirty}


def _aggregate_table_manifest(obj) -> dict[str, Any]:
    """
    Aggregate stats from a TableManifest instance into a compact descriptor.
    """
    parts = obj.partitions.values() if obj and obj.partitions else []
    if not parts:
        return {"rows": 0, "bytes": 0, "tick_min": None, "tick_max": None, "buckets": []}

    rows = 0
    bytes_ = 0
    tick_min: int | None = None
    tick_max: int | None = None
    buckets: set[int] = set()

    for pm in parts:
        rows += int(pm.row_count)
        bytes_ += int(pm.byte_size)
        buckets.add(int(pm.bucket_id))
        if tick_min is None or pm.tick_min < tick_min:
            tick_min = int(pm.tick_min)
        if tick_max is None or pm.tick_max > tick_max:
            tick_max = int(pm.tick_max)

    return {
        "rows": int(rows),
        "bytes": int(bytes_),
        "tick_min": tick_min,
        "tick_max": tick_max,
        "buckets": sorted(buckets),
    }


def collect_tables_index(settings: IoSettings, run_id: RunId) -> dict[str, Any]:
    """
    Build an index of canonical tables for a run by reading per-table manifests.

    Returns:
        dict[str, Any]: Mapping of table_name -> {rows, bytes, tick_min, tick_max, buckets}
    """
    troot = tables_root(settings, str(run_id))
    try:
        names = os.listdir(troot)
    except FileNotFoundError:
        names = []

    out: dict[str, Any] = {}
    for name in sorted(names):
        table_dir = os.path.join(troot, name)
        if not os.path.isdir(table_dir):
            continue
        m = load_manifest(settings, str(run_id), name)
        if m is None:
            continue
        out[name] = _aggregate_table_manifest(m)
    return out


def _relpath_from_run(run_dir: str, abs_path: str) -> str:
    try:
        return os.path.relpath(abs_path, start=run_dir)
    except Exception:
        return abs_path


def collect_artifacts_index(settings: IoSettings, run_id: RunId) -> dict[str, Any]:
    """
    Index lab artifacts (tidy/probes/policy/audit) present under the run's artifacts directory.

    Returns:
        dict[str, Any]: {"lab": {"tidy":[...], "probes":[...], "policy":[...], "audit":[...]}, "world":{}, "mind":{}}
    """
    run_dir = run_root(settings, str(run_id))
    lab_root = os.path.join(run_dir, "artifacts", "lab")

    subdirs = ("tidy", "probes", "policy", "audit")
    idx: dict[str, Any] = {"lab": {k: [] for k in subdirs}, "world": {}, "mind": {}}

    # Optional row counting for parquet via Polars (lazy import)
    try:
        import polars as pl  # type: ignore
    except Exception:
        pl = None  # type: ignore[assignment]

    for sub in subdirs:
        sdir = os.path.join(lab_root, sub)
        try:
            files = os.listdir(sdir)
        except FileNotFoundError:
            files = []
        for fn in sorted(files):
            ap = os.path.join(sdir, fn)
            if not os.path.isfile(ap):
                continue
            entry: dict[str, Any] = {
                "path": _relpath_from_run(run_dir, ap),
                "bytes": int(os.path.getsize(ap)) if os.path.exists(ap) else 0,
            }
            if pl is not None and fn.endswith(".parquet"):
                try:
                    # Prefer a lightweight row count using a tiny scan
                    lf = pl.scan_parquet(ap)
                    n = lf.select([pl.len().alias("_n")]).collect()
                    entry["rows"] = int(n["_n"][0]) if n.height else 0
                except Exception:
                    # Best-effort only
                    pass
            idx["lab"][sub].append(entry)

    return idx


def write_run_bundle_manifest(
    settings: IoSettings,
    run_id: RunId,
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compose and persist the run-bundle manifest atomically.

    Returns:
        dict[str, Any]: The manifest payload that was written.
    """
    run_dir = run_root(settings, str(run_id))
    makedirs(run_dir, exist_ok=True)

    tables_idx = collect_tables_index(settings, run_id)
    # Canonical alias fields: total_rows and total_bytes mirror rows and bytes in bundle tables index
    tables_idx_bc = {
        name: {**entry, "total_rows": entry.get("rows", 0), "total_bytes": entry.get("bytes", 0)}
        for name, entry in tables_idx.items()
    }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "run": {
            "run_id": str(run_id),
            "created_at": _utc_now_iso(),
            "core_schema_v": {
                "major": SCHEMA_V.major,
                "minor": SCHEMA_V.minor,
                "date": SCHEMA_V.date,
            },
            "git": _git_info(),
        },
        "env": {
            "python": sys.version,
            "polars": _safe_pkg_version("polars"),
            "pyarrow": _safe_pkg_version("pyarrow"),
        },
        "io": {
            "root_dir": settings.root_dir,
            "partitioning": settings.partitioning,
            "tick_bucket_size": settings.tick_bucket_size,
            "row_group_size": settings.row_group_size,
            "compression": settings.compression,
        },
        "tables": tables_idx_bc,
        "artifacts": collect_artifacts_index(settings, run_id),
        "meta": meta or {},
    }

    final_path = bundle_manifest_path(settings, run_id)
    tmp_path = final_path + ".tmp"
    data = json.dumps(payload, indent=2).encode("utf-8")
    makedirs(os.path.dirname(final_path), exist_ok=True)
    with open_write(tmp_path) as fh:
        fh.write(data)
    rename_atomic(tmp_path, final_path)
    return payload
