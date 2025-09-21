from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from crv.viz.base import normalize_time_object, scan_parquet_columns

__all__ = [
    "CacheConfig",
    "load_agents_tokens",
    "load_relations",
    "load_other_object",
    "load_object_object",
    "load_events",
    "load_model_specs",
    "get_time_bounds",
    "even_sample",
    "stride_sample",
]

# ---------- Cache configuration (factory of cached callables) ----------


@dataclass(frozen=True)
class CacheConfig:
    """Hashable cache configuration for Streamlit @st.cache_data.

    Note: Streamlit's decorator parameters (ttl, persist) are fixed at decoration
    time. We build and memoize decorated callables per (name, ttl, persist) so the
    app can switch these at runtime while still benefiting from caching.
    """

    ttl: int | None = None
    persist: bool = False


# Registry of decorated functions by (loader_name, CacheConfig)
_CACHE_REGISTRY: dict[tuple[str, CacheConfig], Callable[..., Any]] = {}


def _get_cached(loader_name: str, cfg: CacheConfig, fn: Callable[..., Any]) -> Callable[..., Any]:
    key = (loader_name, cfg)
    if key in _CACHE_REGISTRY:
        return _CACHE_REGISTRY[key]
    # Create a decorated wrapper with desired cache behavior
    if cfg.persist:
        wrapped = st.cache_data(persist="disk", ttl=cfg.ttl)(fn)
    else:
        wrapped = st.cache_data(ttl=cfg.ttl)(fn)
    _CACHE_REGISTRY[key] = wrapped
    return wrapped


# ---------- Internal IO helpers (Polars-first, projection pushdown) ----------


# ---------- Loaders (internal implementations) ----------


def _load_agents_tokens_impl(run_dir: str) -> pl.DataFrame:
    run = Path(run_dir)
    path = run / "agents_tokens.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    # Support Mesa v3+ alternates; normalize -> 't','o'
    cols = [
        "t",
        "step",
        "o",
        "token_id",
        "s_io",
        "value_score",
        "y_io",
        "agent_id",
        "group",
        "s_pos",
        "s_neg",
        "rp",
        "rn",
    ]
    df = scan_parquet_columns(str(path), cols)
    df = normalize_time_object(df)
    return df


def _load_relations_impl(run_dir: str) -> pl.DataFrame | None:
    run = Path(run_dir)
    path = run / "relations.parquet"
    if not path.exists():
        return None
    df = scan_parquet_columns(str(path), ["step", "i", "j", "a_ij"])
    df = normalize_time_object(df)
    # Ensure canonical columns present
    need = {"t", "i", "j", "a_ij"}
    if not need.issubset(set(df.columns)):
        return None
    return df


def _load_other_object_impl(run_dir: str) -> pl.DataFrame | None:
    run = Path(run_dir)
    path = run / "other_object.parquet"
    if not path.exists():
        return None
    df = scan_parquet_columns(str(path), ["step", "i", "j", "o", "b_ijo"])
    df = normalize_time_object(df)
    need = {"t", "i", "j", "o", "b_ijo"}
    if not need.issubset(set(df.columns)):
        return None
    return df


def _load_object_object_impl(run_dir: str) -> pl.DataFrame | None:
    """Load object<->object structure (r_oo) if present; normalize step->t."""
    run = Path(run_dir)
    path = run / "object_object.parquet"
    if not path.exists():
        return None
    df = scan_parquet_columns(str(path), ["step", "i", "o", "op", "r_oo"])
    df = normalize_time_object(df)
    need = {"t", "i", "o", "op", "r_oo"}
    if not need.issubset(set(df.columns)):
        return None
    return df


def _load_events_impl(run_dir: str) -> pl.DataFrame | None:
    """Load events timeline if present; normalize step->t and pass through known fields.

    Expected columns (subset): step|t, type, i, j, o, op, val, mode
    """
    run = Path(run_dir)
    path = run / "events.parquet"
    if not path.exists():
        return None
    desired = [
        "step",
        "t",
        "time_created",
        "type",
        "i",
        "j",
        "o",
        "op",
        "p",
        "val",
        "mode",
        "delivered",
        "received",
        "recipients",
        "content",
        "kind",
        "status",
        "actor",
        "observer",
        "origin",
    ]
    df = scan_parquet_columns(str(path), desired)
    df = normalize_time_object(df)
    # Require at least t and type to be present
    need = {"t", "type"}
    if not need.issubset(set(df.columns)):
        return None
    # Coerce type to string if necessary
    casts: list[pl.Expr] = []
    for column in ("type", "kind", "status", "origin"):
        if column in df.columns and df.schema[column] != pl.Utf8:
            casts.append(pl.col(column).cast(pl.Utf8))
    if casts:
        df = df.with_columns(casts)
    return df


def _load_model_specs_impl(run_dir: str) -> list[dict[str, str]]:
    run = Path(run_dir)
    model_path = run / "model.parquet"
    meta_path = run / "metadata.json"
    specs: dict[str, str] = {}

    try:
        if model_path.exists():
            mdf = pl.read_parquet(model_path)
            if mdf.height > 0:
                row = mdf.row(0, named=True)
                for key in ["seed", "n_agents", "n_tokens", "k", "steps"]:
                    if key in row and row[key] is not None:
                        specs[key] = str(row[key])
        if meta_path.exists():
            meta = pl.read_json(str(meta_path)).to_dicts()
            if meta:
                for key in ["agent_params", "model_params", "experiment_params"]:
                    if key in meta[0]:
                        val = str(meta[0][key])
                        specs[key] = val[:180] + ("..." if len(val) > 180 else "")
    except Exception:
        # Best-effort; return what we have
        pass

    return [{"field": k, "value": v} for k, v in specs.items()]


# ---------- Public loader APIs (dispatch to cached implementations) ----------


def load_agents_tokens(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> pl.DataFrame:
    fn = _get_cached("load_agents_tokens", cfg, _load_agents_tokens_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


def load_relations(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> pl.DataFrame | None:
    fn = _get_cached("load_relations", cfg, _load_relations_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


def load_other_object(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> pl.DataFrame | None:
    fn = _get_cached("load_other_object", cfg, _load_other_object_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


def load_object_object(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> pl.DataFrame | None:
    """Return object_object (r_oo) long table or None if missing."""
    fn = _get_cached("load_object_object", cfg, _load_object_object_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


def load_events(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> pl.DataFrame | None:
    """Return events long table or None if missing."""
    fn = _get_cached("load_events", cfg, _load_events_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


def load_model_specs(run_dir: str, *, cfg: CacheConfig = CacheConfig()) -> list[dict[str, str]]:
    fn = _get_cached("load_model_specs", cfg, _load_model_specs_impl)
    return fn(run_dir)  # type: ignore[no-any-return]


# ---------- Time bounds ----------


def get_time_bounds(df_at: pl.DataFrame) -> tuple[int, int]:
    if "t" not in df_at.columns:
        raise ValueError("get_time_bounds requires a 't' column")
    if df_at.height == 0:
        return (0, 0)
    # Compute scalar min/max via aggregation and extract the first row
    agg = df_at.select(pl.col("t").min().alias("t_min"), pl.col("t").max().alias("t_max"))
    t_min_val, t_max_val = agg.row(0)
    return (int(t_min_val), int(t_max_val))


# ---------- Downsampling helpers (Polars-first) ----------


def even_sample(df: pl.DataFrame, max_points: int) -> pl.DataFrame:
    """Approx evenly-spaced sample by time globally to cap point count.

    - Sort by t (if present), otherwise by row order
    - Compute stride = ceil(n / max_points) and keep every stride-th row
    - Deterministic for fixed input
    """
    if max_points <= 0:
        raise ValueError("max_points must be positive")
    n = df.height
    if n <= max_points:
        return df

    if "t" in df.columns:
        df2 = df.sort("t")
    else:
        df2 = df.clone()

    stride = max((n + max_points - 1) // max_points, 1)
    return df2.with_row_index(name="_rn").filter(pl.col("_rn") % stride == 0).drop("_rn")


def stride_sample(df: pl.DataFrame, stride: int) -> pl.DataFrame:
    """Keep every k-th row by time order (or original order if t missing)."""
    if stride <= 1:
        return df
    if "t" in df.columns:
        df2 = df.sort("t")
    else:
        df2 = df.clone()
    return df2.with_row_index(name="_rn").filter(pl.col("_rn") % stride == 0).drop("_rn")
