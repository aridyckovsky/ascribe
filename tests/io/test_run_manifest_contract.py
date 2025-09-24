from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.run_manifest import collect_tables_index, write_run_bundle_manifest


def _make_identity_edges_df(n: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "tick": list(range(n)),
            "observer_agent_id": [f"A{i % 3}" for i in range(n)],
            "edge_kind": ["self_to_object"] * n,
            "edge_weight": [float(i) for i in range(n)],
        }
    )


def _make_exchange_df(ticks: list[int]) -> pl.DataFrame:
    # Minimal required columns for EXCHANGE
    return pl.DataFrame(
        {
            "tick": ticks,
            "venue_id": ["venue_central"] * len(ticks),
            "token_id": ["0"] * len(ticks),
            "exchange_event_type": ["trade"] * len(ticks),
            "additional_payload": [{"legs": 1}] * len(ticks),
        }
    )


def _assert_table_entry_contract(name: str, entry: dict[str, Any]) -> None:
    # Required keys
    for k in ("rows", "bytes", "total_rows", "total_bytes", "tick_min", "tick_max", "buckets"):
        assert k in entry, f"missing key {k} for table {name}"
    # Types and relations
    assert isinstance(entry["rows"], int) and entry["rows"] >= 1
    assert isinstance(entry["bytes"], int) and entry["bytes"] >= 0
    assert isinstance(entry["total_rows"], int) and entry["total_rows"] == entry["rows"]
    assert isinstance(entry["total_bytes"], int) and entry["total_bytes"] == entry["bytes"]
    assert isinstance(entry["buckets"], list) and all(isinstance(b, int) for b in entry["buckets"])
    assert (entry["tick_min"] is None) == (entry["tick_max"] is None) or (
        isinstance(entry["tick_min"], int) and isinstance(entry["tick_max"], int)
    )
    if isinstance(entry["tick_min"], int) and isinstance(entry["tick_max"], int):
        assert entry["tick_min"] <= entry["tick_max"]


def test_bundle_tables_index_contract_multiple_tables(tmp_path: Path) -> None:
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=50)
    run_id = RunId("20250108-000000")
    ds = Dataset(settings, run_id)

    # Write two canonical tables to produce manifests
    ds.append(TableName.IDENTITY_EDGES, _make_identity_edges_df(25))  # spans bucket 0
    ds.append(TableName.EXCHANGE, _make_exchange_df(list(range(10, 15))))  # ticks in bucket 0

    # Generate bundle manifest (meta optional)
    payload = write_run_bundle_manifest(settings, run_id)
    tables = payload.get("tables", {})
    assert TableName.IDENTITY_EDGES.value in tables
    assert TableName.EXCHANGE.value in tables

    # Contract checks for both tables
    ident = tables[TableName.IDENTITY_EDGES.value]
    ex = tables[TableName.EXCHANGE.value]
    _assert_table_entry_contract(TableName.IDENTITY_EDGES.value, ident)
    _assert_table_entry_contract(TableName.EXCHANGE.value, ex)

    # Strength: rows in tables index must equal sum of per-table manifest row_count
    m_ident = ds.manifest(TableName.IDENTITY_EDGES)
    m_ex = ds.manifest(TableName.EXCHANGE)
    assert m_ident is not None and m_ex is not None

    total_ident = sum(pm.row_count for pm in m_ident.partitions.values())
    total_ex = sum(pm.row_count for pm in m_ex.partitions.values())
    assert total_ident == ident["rows"]
    assert total_ex == ex["rows"]

    # Verify collect_tables_index mirrors base fields used by bundle index
    base_idx = collect_tables_index(settings, run_id)
    assert base_idx[TableName.IDENTITY_EDGES.value]["rows"] == ident["rows"]
    assert base_idx[TableName.EXCHANGE.value]["bytes"] == ex["bytes"]


def test_bundle_tables_index_empty_when_no_tables(tmp_path: Path) -> None:
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=50)
    run_id = RunId("20250109-000000")

    # No appends: indexes should be empty
    idx = collect_tables_index(settings, run_id)
    assert idx == {}

    payload = write_run_bundle_manifest(settings, run_id)
    assert payload.get("tables", {}) == {}
