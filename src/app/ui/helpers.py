"""
Shared UI helper utilities for the CRV Streamlit application.

This module centralizes small cross-cutting helpers (accelerators, time formatting,
quick KPI computations) used by multiple UI components. Keeping these here avoids
circular imports and makes per-tab modules leaner.

Notes:
    - All functions include Google-style docstrings.
    - This module is UI-adjacent (uses Altair and Streamlit-friendly utilities)
      but contains no Streamlit state manipulation itself.
"""

from __future__ import annotations

from datetime import UTC, datetime

import altair as alt
import polars as pl


def enable_vegafusion_optional() -> str | None:
    """Attempt to enable the VegaFusion accelerator for Altair if available.

    Returns:
        str | None: Short status message if enabling succeeded, otherwise None.

    Notes:
        This is an optional performance accelerator. If the environment does not
        have VegaFusion installed or configured, the function will fail silently
        and return None.
    """
    try:
        alt.data_transformers.enable("vegafusion")
        return "VegaFusion enabled (optional accelerator)."
    except Exception:
        return None


def humanize_ago(ts: float) -> str:
    """Convert a UNIX timestamp into a short humanized age string.

    Args:
        ts (float): UNIX timestamp (seconds since epoch).

    Returns:
        str: Humanized string like "32s ago", "5m ago", "2h ago", "3d ago",
        or "n/a" if conversion fails.
    """
    try:
        dt = datetime.fromtimestamp(ts, tz=UTC)
        now = datetime.now(tz=UTC)
        delta = (now - dt).total_seconds()
        if delta < 60:
            return f"{int(delta)}s ago"
        if delta < 3600:
            return f"{int(delta // 60)}m ago"
        if delta < 86400:
            return f"{int(delta // 3600)}h ago"
        return f"{int(delta // 86400)}d ago"
    except Exception:
        return "n/a"


def format_ts(ts: float) -> str:
    """Format a UNIX timestamp as a local datetime string.

    Args:
        ts (float): UNIX timestamp (seconds since epoch).

    Returns:
        str: Formatted timestamp "YYYY-MM-DD HH:MM:SS", or "n/a" on failure.
    """
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "n/a"


def compute_overview_kpis(at_df: pl.DataFrame) -> dict[str, float]:
    """Compute quick KPI metrics from a normalized agents_tokens DataFrame.

    Computes:
        - final_mean_value: Mean of value_score at the final time t.
        - final_hold_rate: Share of rows with y_io == 1 at the final time t.

    Args:
        at_df (pl.DataFrame): Normalized agents_tokens Polars DataFrame. Expected
            to include column "t". If not present, zeros are returned.

    Returns:
        dict[str, float]: KPI dictionary with keys "final_mean_value" and "final_hold_rate".
    """
    if at_df.is_empty() or "t" not in at_df.columns:
        return {"final_mean_value": 0.0, "final_hold_rate": 0.0}
    # Use aggregation to avoid Optional typing issues with Series.max
    tmax_df = at_df.select(pl.col("t").max().alias("_tmax"))
    t_max = int(tmax_df.get_column("_tmax").item())
    last = at_df.filter(pl.col("t") == t_max)
    # Mean valuation (robust scalar extraction)
    if "value_score" in last.columns:
        mdf = last.select(pl.col("value_score").mean().alias("_m"))
        mean_val = float(mdf.get_column("_m").item())
    else:
        mean_val = 0.0
    # Holdings rate (share of y_io == 1)
    if "y_io" in last.columns:
        hr_df = last.with_columns(((pl.col("y_io") == 1).cast(pl.Float64)).alias("_held")).select(
            pl.col("_held").mean().alias("_m")
        )
        hold_rate = float(hr_df.get_column("_m").item())
    else:
        hold_rate = 0.0
    return {"final_mean_value": mean_val, "final_hold_rate": hold_rate}
