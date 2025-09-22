from __future__ import annotations

import json
import os
from pathlib import Path

import polars as pl

from crv.core.grammar import TableName
from crv.core.ids import RunId
from crv.io.config import IoSettings
from crv.io.dataset import Dataset
from crv.io.paths import run_root
from crv.io.run_manifest import (
    collect_artifacts_index,
    collect_tables_index,
    write_run_bundle_manifest,
)
from crv.lab.io_helpers import write_tidy


def _make_identity_edges_df(ticks: list[int]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "tick": ticks,
            "observer_agent_id": [f"A{i % 2}" for i in range(len(ticks))],
            "edge_kind": ["self_to_object"] * len(ticks),
            "edge_weight": [float(i) for i in range(len(ticks))],
        }
    )


def test_collect_tables_and_artifacts_index(tmp_path: Path) -> None:
    settings = IoSettings(root_dir=str(tmp_path), tick_bucket_size=50)
    run_id = RunId("20250105-000000")

    # 1) Create canonical table files via Dataset.append()
    ds = Dataset(settings, run_id)
    df = _make_identity_edges_df(list(range(0, 75)))  # spans two buckets
    ds.append(TableName.IDENTITY_EDGES, df)

    # 2) Create lab artifacts (tidy parquet) using io_helpers
    tidy_df = pl.DataFrame(
        {
            "answer": [1, 2, 3],
            "value": [1, 2, 2],
            "ctx_token_kind": ["o0", "o0", "o1"],
            "persona": ["p", "p", "p"],
            "model": ["m", "m", "m"],
        }
    )
    write_tidy(settings, run_id, tidy_df, filename="tidy_demo.parquet")

    # 3) Verify tables index
    tables_idx = collect_tables_index(settings, run_id)
    assert TableName.IDENTITY_EDGES.value in tables_idx
    ident = tables_idx[TableName.IDENTITY_EDGES.value]
    assert ident["rows"] == 75
    assert set(ident["buckets"]) == {0, 1}
    assert ident["tick_min"] is not None and ident["tick_max"] is not None

    # 4) Verify artifacts index (should include tidy file with bytes and optional row count)
    artifacts_idx = collect_artifacts_index(settings, run_id)
    lab_tidy = artifacts_idx.get("lab", {}).get("tidy", [])
    assert any(e.get("path", "").endswith("tidy_demo.parquet") for e in lab_tidy)
    # Ensure bytes are populated and rows present (best-effort)
    entry = next(e for e in lab_tidy if e.get("path", "").endswith("tidy_demo.parquet"))
    assert entry.get("bytes", 0) > 0
    # rows may be omitted if Polars scanning fails in env, but usually present
    if "rows" in entry:
        assert entry["rows"] == 3

    # 5) Write the run bundle manifest and ensure it reflects current state
    payload = write_run_bundle_manifest(settings, run_id, meta={"test": True})
    assert payload["tables"][TableName.IDENTITY_EDGES.value]["rows"] == 75
    assert any(
        e.get("path", "").endswith("tidy_demo.parquet") for e in payload["artifacts"]["lab"]["tidy"]
    )

    # Manifest file exists on disk
    run_dir = run_root(settings, str(run_id))
    path_bundle = os.path.join(run_dir, "bundle.manifest.json")
    assert os.path.exists(path_bundle)
    # Validate minimal JSON shape
    loaded = json.loads(Path(path_bundle).read_text())
    assert loaded.get("io", {}).get("root_dir") == settings.root_dir
    assert "schema_version" in loaded and "run" in loaded and "env" in loaded
