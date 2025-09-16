from crv.world.config import AgentParams, ExperimentParams, ModelParams
from crv.world.model import CRVModel


def test_model_runs_steps(tmp_path):
    out_dir = tmp_path / "run"
    ap = AgentParams(k=1)
    mp = ModelParams(n=6, k=1)
    ep = ExperimentParams(
        steps=10, seed=321, out_dir=str(out_dir), save_csv=False, save_parquet=False
    )
    m = CRVModel(ap, mp, ep)
    m.init_two_group_identity()
    for _ in range(ep.steps):
        m.step()
    assert m.step_idx == ep.steps
