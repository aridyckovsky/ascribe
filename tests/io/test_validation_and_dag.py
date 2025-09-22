import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.errors import IoSchemaError


def test_validation_extra_columns_strict(tmp_path: Path):
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=100, strict_schema=True)
    run_id = RunId("20250104-000000")
    ds = Dataset(settings, run_id)

    # Minimal required columns for IDENTITY_EDGES + an unexpected extra column 'foo'
    df = pl.DataFrame(
        {
            "tick": [0, 1, 2],
            "observer_agent_id": ["A0", "A1", "A2"],
            "edge_kind": ["self_to_object", "self_to_object", "self_to_object"],
            "edge_weight": [0.0, 1.0, 2.0],
            "foo": [1, 2, 3],  # unexpected
        }
    )
    with pytest.raises(IoSchemaError):
        ds.append(TableName.IDENTITY_EDGES, df)


def test_import_dag_no_side_imports():
    # Run in a clean Python process to avoid pollution from other tests
    forbidden = ["crv.world", "crv.mind", "crv.lab", "crv.viz", "app"]
    code = r"""
import sys
import importlib
import crv.io  # noqa: F401

forbidden = ["crv.world", "crv.mind", "crv.lab", "crv.viz", "app"]
present = [m for m in forbidden if m in sys.modules]
print(",".join(present))
"""
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    present = proc.stdout.strip()
    # On a clean import of crv.io, none of the forbidden modules should be imported transitively.
    assert present == ""
