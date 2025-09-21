from __future__ import annotations

import time

import polars as pl

from app.ui.helpers import compute_overview_kpis, format_ts, humanize_ago


def test_humanize_ago_and_format_ts_smoke() -> None:
    now = time.time()
    assert "ago" in humanize_ago(now - 2)
    assert isinstance(format_ts(now), str) and len(format_ts(now)) >= 10


def test_compute_overview_kpis_uses_final_t_and_aggregates_mean_and_hold_rate() -> None:
    # Two timesteps; final timestep has two rows to verify mean and holdings rate aggregation.
    df = pl.DataFrame(
        {
            "t": [0, 1, 1],
            "value_score": [0.10, 0.30, 0.50],
            "y_io": [0, 1, 0],
        }
    )
    kpi = compute_overview_kpis(df)
    # Final t = 1; mean(value_score) = (0.30 + 0.50)/2 = 0.40; hold rate = mean([1,0]) = 0.5
    assert abs(kpi["final_mean_value"] - 0.40) < 1e-9
    assert abs(kpi["final_hold_rate"] - 0.50) < 1e-9


def test_compute_overview_kpis_handles_missing_columns_gracefully() -> None:
    # Missing value_score and y_io should yield zeros without raising.
    df = pl.DataFrame({"t": [0, 1], "agent_id": [0, 0]})
    kpi = compute_overview_kpis(df)
    assert kpi == {"final_mean_value": 0.0, "final_hold_rate": 0.0}
