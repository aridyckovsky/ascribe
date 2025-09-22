import glob
import os
from pathlib import Path

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.manifest import load_manifest
from crv.io.paths import bucket_dir, table_dir


def make_identity_edges_df(ticks: list[int]) -> pl.DataFrame:
    # Minimal required columns for IDENTITY_EDGES
    return pl.DataFrame(
        {
            "tick": ticks,
            "observer_agent_id": [f"A{i % 3}" for i in range(len(ticks))],
            "edge_kind": ["self_to_object"] * len(ticks),
            "edge_weight": [float(i) for i in range(len(ticks))],
        }
    )


def test_append_creates_parts_and_manifest(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=100)
    run_id = RunId("20250101-000000")
    ds = Dataset(settings, run_id)

    # Two buckets worth of rows: ticks 0..149 => buckets 0 and 1
    df = make_identity_edges_df(list(range(150)))
    summary = ds.append(TableName.IDENTITY_EDGES, df)

    # Summary sanity
    assert summary["table"] == TableName.IDENTITY_EDGES.value
    assert summary["run_id"] == run_id
    assert summary["rows"] == 150
    assert set(summary["buckets"]) == {0, 1}
    assert len(summary["parts"]) >= 2  # at least one part per bucket

    # Check files exist, and no lingering .tmp files
    tdir = table_dir(settings, run_id, TableName.IDENTITY_EDGES.value)
    assert os.path.isdir(tdir)

    for b in summary["buckets"]:
        bdir = bucket_dir(settings, run_id, TableName.IDENTITY_EDGES.value, b)
        assert os.path.isdir(bdir)
        # No *.tmp should remain
        tmps = glob.glob(os.path.join(bdir, "*.tmp"))
        assert tmps == []
        # At least one parquet exists
        parts = [p for p in os.listdir(bdir) if p.endswith(".parquet")]
        assert parts, f"no parquet parts found in {bdir}"

    # Manifest exists and has content
    manifest = load_manifest(settings, run_id, TableName.IDENTITY_EDGES.value)
    assert manifest is not None
    # There should be entries for both buckets
    bucket_keys = set(manifest.partitions.keys())
    assert {"000000", "000001"}.issubset(bucket_keys)
    # Totals are plausible
    total_rows = sum(pm.row_count for pm in manifest.partitions.values())
    assert total_rows == 150
    # Tick ranges are plausible
    for pm in manifest.partitions.values():
        assert pm.tick_min <= pm.tick_max
        assert pm.row_count > 0
        assert pm.byte_size >= 0


def test_scan_pruning_on_tick_range(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=100)
    run_id = RunId("20250102-000000")
    ds = Dataset(settings, run_id)

    # Write two disjoint buckets
    df1 = make_identity_edges_df(list(range(0, 100)))  # bucket 0
    df2 = make_identity_edges_df(list(range(100, 200)))  # bucket 1
    ds.append(TableName.IDENTITY_EDGES, df1)
    ds.append(TableName.IDENTITY_EDGES, df2)

    # Query overlapping both buckets partially
    lf = ds.scan(TableName.IDENTITY_EDGES, where={"tick_min": 50, "tick_max": 120})
    out = lf.collect()
    assert out.height > 0
    assert out["tick"].min() >= 50
    assert out["tick"].max() <= 120
    # Ensure we touched both buckets (presence of ticks from both sides)
    assert out["tick"].min() <= 99
    assert out["tick"].max() >= 100


def test_rebuild_manifest_from_fs(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=50)
    run_id = RunId("20250103-000000")
    ds = Dataset(settings, run_id)

    df = make_identity_edges_df(list(range(0, 75)))  # buckets 0 and 1 (0..49, 50..74)
    ds.append(TableName.IDENTITY_EDGES, df)

    # Remove manifest.json to force rebuild
    tdir = table_dir(settings, run_id, TableName.IDENTITY_EDGES.value)
    mpath = os.path.join(tdir, "manifest.json")
    assert os.path.exists(mpath)
    os.remove(mpath)
    assert not os.path.exists(mpath)

    # Rebuild and verify
    rebuilt = ds.rebuild_manifest(TableName.IDENTITY_EDGES)
    assert rebuilt is not None
    assert os.path.exists(mpath)
    # Partitions should cover two buckets
    assert {"000000", "000001"} == set(rebuilt.partitions.keys())
    total = sum(pm.row_count for pm in rebuilt.partitions.values())
    assert total == 75
