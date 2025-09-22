import os
from pathlib import Path

import polars as pl
import pytest

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.errors import IoManifestError, IoSchemaError
from crv.io.paths import table_dir


def test_required_missing_column_raises(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path))
    ds = Dataset(settings, run_id=RunId("run_missing_required"))

    # Missing required column 'edge_weight' for IDENTITY_EDGES
    df = pl.DataFrame(
        {
            "tick": [0, 1, 2],
            "observer_agent_id": ["A0", "A1", "A2"],
            "edge_kind": ["self_to_object"] * 3,
            # edge_weight omitted
        }
    )
    with pytest.raises(IoSchemaError):
        ds.append(TableName.IDENTITY_EDGES, df)


def test_scalar_casting_for_required_types(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path))
    ds = Dataset(settings, run_id=RunId("run_cast_scalars"))

    # edge_weight should be f64; provide as ints to exercise casting
    df = pl.DataFrame(
        {
            "tick": [0, 1, 2],
            "observer_agent_id": ["A0", "A1", "A2"],
            "edge_kind": ["self_to_object"] * 3,
            "edge_weight": [0, 1, 2],  # Ints; validator should cast to Float64
        }
    )
    out = ds.append(TableName.IDENTITY_EDGES, df)
    assert out["rows"] == 3


def test_non_strict_allows_extra_columns(tmp_path: Path):
    # strict_schema=False should allow extra columns beyond descriptor
    settings = IoSettings(root_dir=str(tmp_path), strict_schema=False)
    ds = Dataset(settings, run_id=RunId("run_non_strict"))

    df = pl.DataFrame(
        {
            "tick": [0, 1],
            "observer_agent_id": ["A0", "A1"],
            "edge_kind": ["self_to_object", "self_to_object"],
            "edge_weight": [0.0, 1.0],
            "extra_col": [123, 456],  # extra; allowed in non-strict mode
        }
    )
    out = ds.append(TableName.IDENTITY_EDGES, df)
    assert out["rows"] == 2


def test_scan_without_manifest_falls_back_to_fs(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path))
    run_id = RunId("run_without_manifest")
    ds = Dataset(settings, run_id)

    df = pl.DataFrame(
        {
            "tick": list(range(0, 20)),  # should create at least one bucket
            "observer_agent_id": ["A"] * 20,
            "edge_kind": ["self_to_object"] * 20,
            "edge_weight": [float(i) for i in range(20)],
        }
    )
    ds.append(TableName.IDENTITY_EDGES, df)

    # Remove manifest.json to force FS-walk fallback in scan()
    tdir = table_dir(settings, run_id, TableName.IDENTITY_EDGES.value)
    mpath = os.path.join(tdir, "manifest.json")
    assert os.path.exists(mpath)
    os.remove(mpath)
    assert not os.path.exists(mpath)

    with pytest.raises(IoManifestError):
        ds.scan(TableName.IDENTITY_EDGES)
    # After rebuild, scanning should succeed and yield the original 20 rows
    ds.rebuild_manifest(TableName.IDENTITY_EDGES)
    out = ds.read(TableName.IDENTITY_EDGES)
    assert out.height == 20
