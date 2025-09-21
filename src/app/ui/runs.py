"""
Run discovery and demo-run utilities for the CRV Streamlit UI.

This module encapsulates:
- Run directory scanning under one or more roots.
- Minimal demo run creation to bootstrap the UI when no runs exist.
- A cached wrapper around run listing suitable for Streamlit usage.

Notes:
    - File-system operations are localized here.
    - Streamlit caching is provided via `cached_list_runs`.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

# Public constants
IGNORED_DIRS: set[str] = {".venv", "site", ".git", "node_modules", "__pycache__"}


def list_recent_runs_under(base: Path) -> Iterable[Path]:
    """Yield candidate self-contained run directories under a base folder.

    A run is considered self-contained if it contains:
      - agents_tokens.parquet, and at least one of:
        * model.parquet
        * metadata.json
        * manifest_*.json

    Args:
        base (Path): Base directory to scan recursively.

    Yields:
        Path: Paths to run directories that satisfy the conditions.

    Notes:
        - Directory trees matching IGNORED_DIRS are skipped.
        - This function is IO-bound and intended to be called from a cached wrapper.
    """
    if not base.exists() or not base.is_dir():
        return []
    for p in base.rglob("*"):
        if not p.is_dir():
            continue
        if any(seg in IGNORED_DIRS for seg in p.parts):
            continue
        at = p / "agents_tokens.parquet"
        if not at.exists():
            continue
        model_ok = (p / "model.parquet").exists() or (p / "metadata.json").exists()
        manifest_ok = any(
            child.name.startswith("manifest_") and child.suffix == ".json"
            for child in p.glob("manifest_*.json")
        )
        if model_ok or manifest_ok:
            yield p


def list_runs_impl(roots: list[str], limit: int = 200) -> list[dict[str, Any]]:
    """Return a list of recent runs with minimal metadata for header selector.

    Args:
        roots (list[str]): Root directories to scan (absolute or relative paths).
        limit (int): Maximum number of run candidates to return (best-effort).

    Returns:
        list[dict[str, Any]]: Run metadata dicts with keys: "path", "name", "mtime".

    Notes:
        - Resolves duplicates by absolute path.
        - Prefers leaf-most directories and sorts by recency (mtime).
    """
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for root in roots:
        base = Path(root)
        for p in list_recent_runs_under(base):
            sp = str(p.resolve())
            if sp in seen:
                continue
            seen.add(sp)
            try:
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0.0
            items.append({"path": sp, "name": p.name, "mtime": mtime})

    # Prefer deeper paths first (leaves), then prune ancestors, then sort by recency.
    items_by_depth = sorted(items, key=lambda d: len(Path(d["path"]).parts), reverse=True)
    pruned: list[dict[str, Any]] = []
    kept_paths: list[Path] = []
    for d in items_by_depth:
        p = Path(d["path"])
        if any(str(kp).startswith(str(p) + os.sep) or str(kp) == str(p) for kp in kept_paths):
            continue
        pruned.append(d)
        kept_paths.append(p)
        if len(pruned) >= limit:
            break

    pruned.sort(key=lambda d: d["mtime"], reverse=True)
    return pruned


@st.cache_data(ttl=10)
def cached_list_runs(roots: tuple[str, ...], limit: int = 200) -> list[dict[str, Any]]:
    """Streamlit-cached wrapper for listing runs.

    Args:
        roots (tuple[str, ...]): Root directories to scan.
        limit (int): Maximum number of entries (best-effort).

    Returns:
        list[dict[str, Any]]: Run metadata entries.

    Notes:
        The default ttl is short; callers can control refresh by varying inputs or
        using a session-state bump to re-key calls.
    """
    return list_runs_impl(list(roots), limit)


def create_min_demo_run(run_dir: Path) -> None:
    """Create a minimal demo run with required Parquet files.

    Args:
        run_dir (Path): Target directory to create or populate.

    Returns:
        None

    Notes:
        - Creates agents_tokens.parquet with minimal Mesa v3+ schema.
        - Creates relations.parquet and other_object.parquet with minimal content.
        - Creates model.parquet with minimal specs.
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    # Minimal agents_tokens with Mesa v3+ schema (step->t, token_id->o normalization downstream)
    at = pl.DataFrame(
        {
            "step": [0, 0, 1, 1, 2, 2],
            "agent_id": [0, 1, 0, 1, 0, 1],
            "token_id": [0, 1, 0, 1, 0, 1],
            "s_io": [0.1, 0.2, 0.3, 0.25, 0.35, 0.4],
            "value_score": [0.2, 0.25, 0.3, 0.32, 0.33, 0.36],
            "y_io": [0, 1, 1, 1, 1, 1],
            "group": ["A", "A", "A", "B", "B", "B"],
        }
    )
    at.write_parquet(run_dir / "agents_tokens.parquet")

    # Minimal relations and other_object
    rel = pl.DataFrame({"step": [0, 0], "i": [0, 1], "j": [1, 0], "a_ij": [0.8, -0.3]})
    rel.write_parquet(run_dir / "relations.parquet")

    bdf = pl.DataFrame(
        {"step": [0, 0], "i": [0, 0], "j": [1, 1], "o": [0, 1], "b_ijo": [0.5, -0.2]}
    )
    bdf.write_parquet(run_dir / "other_object.parquet")

    # Minimal model.parquet for specs
    model = pl.DataFrame({"seed": [123], "n_agents": [2], "n_tokens": [2], "k": [1], "steps": [3]})
    model.write_parquet(run_dir / "model.parquet")
