from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from app.ui.runs import cached_list_runs, create_min_demo_run, list_runs_impl


def _write_min_agents_tokens(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(
        {
            "step": [0, 1],
            "agent_id": [0, 0],
            "token_id": [0, 1],
            "s_io": [0.1, 0.2],
            "value_score": [0.2, 0.3],
            "y_io": [0, 1],
        }
    )
    df.write_parquet(p)


def _write_min_model_parquet(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {"seed": [1], "n_agents": [1], "n_tokens": [2], "k": [1], "steps": [2]}
    ).write_parquet(p)


def test_create_min_demo_run_produces_required_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "demo_run"
    create_min_demo_run(run_dir)
    assert (run_dir / "agents_tokens.parquet").exists()
    assert (run_dir / "relations.parquet").exists()
    assert (run_dir / "other_object.parquet").exists()
    assert (run_dir / "model.parquet").exists()

    # And discovery should find this run under the tmp root
    runs = list_runs_impl([str(tmp_path)], 200)
    paths = {r["path"] for r in runs}
    assert str(run_dir.resolve()) in paths


def test_list_runs_impl_prefers_leaf_most_and_prunes_ancestors(tmp_path: Path) -> None:
    # Create an ancestor directory that is a "run"
    run_ancestor = tmp_path / "runs" / "A"
    _write_min_agents_tokens(run_ancestor / "agents_tokens.parquet")
    _write_min_model_parquet(run_ancestor / "model.parquet")

    # Create a nested child run under the ancestor (deeper path)
    run_child = run_ancestor / "child"
    _write_min_agents_tokens(run_child / "agents_tokens.parquet")
    _write_min_model_parquet(run_child / "model.parquet")

    # Discovery under the common root should include only the deeper leaf (child), not the ancestor
    runs = list_runs_impl([str(tmp_path)], 200)
    found = {Path(r["path"]).resolve() for r in runs}
    assert run_child.resolve() in found
    assert run_ancestor.resolve() not in found, (
        "Ancestor should be pruned when a deeper child exists"
    )


@pytest.mark.parametrize("use_model, use_manifest", [(True, False), (False, True), (True, True)])
def test_list_runs_impl_accepts_runs_with_model_or_manifest(
    tmp_path: Path, use_model: bool, use_manifest: bool
) -> None:
    # Construct a valid run containing agents_tokens and either model.parquet or manifest_*.json
    run_dir = tmp_path / "valid"
    _write_min_agents_tokens(run_dir / "agents_tokens.parquet")
    if use_model:
        _write_min_model_parquet(run_dir / "model.parquet")
    if use_manifest:
        (run_dir / "manifest_any.json").write_text("{}", encoding="utf-8")

    runs = list_runs_impl([str(tmp_path)], 200)
    paths = {r["path"] for r in runs}
    assert str(run_dir.resolve()) in paths


def test_cached_list_runs_matches_uncached(tmp_path: Path) -> None:
    # Prepare two runs to exercise ordering and caching
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    _write_min_agents_tokens(r1 / "agents_tokens.parquet")
    _write_min_model_parquet(r1 / "model.parquet")
    _write_min_agents_tokens(r2 / "agents_tokens.parquet")
    _write_min_model_parquet(r2 / "model.parquet")

    uncached = list_runs_impl([str(tmp_path)], 200)
    cached = cached_list_runs((str(tmp_path),), 200)
    # Compare by sorted path sets (ordering by mtime may differ slightly across FS ops)
    u_paths = sorted({r["path"] for r in uncached})
    c_paths = sorted({r["path"] for r in cached})
    assert u_paths == c_paths, (
        "cached_list_runs should reflect list_runs_impl results for same roots"
    )
