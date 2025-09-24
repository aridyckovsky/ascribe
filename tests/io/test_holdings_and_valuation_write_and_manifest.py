from __future__ import annotations

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.run_manifest import write_run_bundle_manifest


def test_holdings_and_valuation_append_and_manifest(tmp_path) -> None:
    settings = IoSettings(root_dir=str(tmp_path), strict_schema=True, tick_bucket_size=100)
    run_id = RunId("20250105-000000")
    ds = Dataset(settings, run_id)

    # Minimal valid holdings frame (required columns only)
    df_hold = pl.DataFrame(
        {
            "tick": [0, 0, 0],
            "agent_id": ["0", "1", "2"],
            "token_id": ["0", "0", "0"],
            "quantity": [1, 0, 1],
        }
    )
    s1 = ds.append(TableName.HOLDINGS, df_hold)
    assert s1["rows"] == df_hold.height

    # Minimal valuation frame (quantity + nullable valuation fields)
    # Provide provenance strings (not required to be non-null but allowed)
    df_val = pl.DataFrame(
        {
            "tick": [0, 0, 0],
            "agent_id": ["0", "1", "2"],
            "token_id": ["0", "0", "0"],
            "quantity": [1, 0, 1],
            "avg_unit_cost": [None, None, None],
            "cost_value": [None, None, None],
            "mark_price": [None, None, None],
            "mark_value": [None, None, None],
            "realized_pnl": [None, None, None],
            "unrealized_pnl": [None, None, None],
            "price_source": ["last_trade", "last_trade", "last_trade"],
            "accounting_method": ["wac", "wac", "wac"],
        }
    )
    s2 = ds.append(TableName.HOLDINGS_VALUATION, df_val)
    assert s2["rows"] == df_val.height

    # Read back to ensure schema and materialization
    out_hold = ds.read(TableName.HOLDINGS)
    out_val = ds.read(TableName.HOLDINGS_VALUATION)
    assert out_hold.height == df_hold.height
    assert out_val.height == df_val.height
    for col in ("tick", "agent_id", "token_id", "quantity"):
        assert col in out_hold.columns
        assert col in out_val.columns

    # Manifest should include both tables
    bundle = write_run_bundle_manifest(settings, run_id, meta={"test": True})
    tables_idx = bundle.get("tables", {})
    assert TableName.HOLDINGS.value in tables_idx
    assert TableName.HOLDINGS_VALUATION.value in tables_idx
    assert tables_idx[TableName.HOLDINGS.value]["total_rows"] >= 1
    assert tables_idx[TableName.HOLDINGS_VALUATION.value]["total_rows"] >= 1
