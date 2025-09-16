from __future__ import annotations

from pathlib import Path

import polars as pl

from crv.lab.policy_builder import (
    PolicyBuildConfig,
    aggregate_policy,
    load_scenarios,
    run_mock,
    tidy_results,
    write_manifest,
    write_policy,
)
from crv.lab.survey import SURVEY_ID
from crv.world.sim import main as sim_main


def _build_mock_policy(out_dir: Path) -> Path:
    cfg = PolicyBuildConfig(
        scenarios_path=Path("nonexistent_demo_scenarios.parquet"),  # triggers synthesis
        personas=["persona_baseline"],
        models=["gpt-4o"],
        out_dir=out_dir,
        seed=123,
        survey_id=SURVEY_ID,
    )
    scenarios_df = load_scenarios(cfg.scenarios_path)
    raw = run_mock(cfg, scenarios_df)
    tidy = tidy_results(raw)
    policy = aggregate_policy(tidy)
    policy_path = write_policy(policy, out_dir)
    write_manifest(
        {
            "survey_id": cfg.survey_id,
            "seed": cfg.seed,
            "mode": "mock",
            "rows_raw": int(tidy.height),
            "rows_policy": int(policy.height),
            "out_dir": str(out_dir),
            "policy_path": str(policy_path),
        },
        out_dir,
    )
    return policy_path


def test_mock_policy_builds(tmp_path: Path) -> None:
    out_dir = tmp_path / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    policy_path = _build_mock_policy(out_dir)

    assert policy_path.exists(), "Policy parquet should exist"

    df = pl.read_parquet(policy_path)
    required_cols = {
        "ctx_token_kind",
        "ctx_owner_status",
        "ctx_peer_alignment",
        "persona",
        "model",
        "value_mean",
        "value_sd",
        "n",
    }
    assert required_cols.issubset(set(df.columns)), (
        f"Missing columns in policy: {required_cols - set(df.columns)}"
    )
    assert df.height >= 1, "Policy should contain at least one row"


def test_sim_consumes_policy(tmp_path: Path) -> None:
    # 1) Build mock policy
    policy_dir = tmp_path / "demo"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_path = _build_mock_policy(policy_dir)

    # 2) Run a short simulation using that policy
    out_dir = tmp_path / "sim_out"
    args = [
        "--policy",
        str(policy_path),
        "--steps",
        "3",
        "--n",
        "4",
        "--k",
        "1",
        "--out",
        str(out_dir),
    ]
    sim_main(args)

    # 3) Verify expected outputs exist and have basic schema
    model_parquet = out_dir / "model.parquet"
    agents_tokens_parquet = out_dir / "agents_tokens.parquet"
    assert model_parquet.exists(), "Model parquet should exist"
    assert agents_tokens_parquet.exists(), "Agents tokens parquet should exist"

    df_model = pl.read_parquet(model_parquet)
    assert {"step", "seed", "n_agents", "n_tokens"}.issubset(set(df_model.columns))

    df_agents = pl.read_parquet(agents_tokens_parquet)
    # Minimal required columns emitted by CRVDataCollector
    expected_agent_cols = {
        "step",
        "agent_id",
        "token_id",
        "s_io",
        "rp",
        "rn",
        "y_io",
        "value_score",
    }
    assert expected_agent_cols.issubset(set(df_agents.columns)), (
        f"Missing agent cols: {expected_agent_cols - set(df_agents.columns)}"
    )
