from crv.world.config import AgentParams, ExperimentParams, ModelParams
from crv.world.model import CRVModel


def test_model_init():
    ap = AgentParams(k=1)
    mp = ModelParams(n=4, k=1)
    ep = ExperimentParams(steps=5, seed=123, out_dir="out/test-init")
    m = CRVModel(ap, mp, ep)
    assert len(m.agents_list) == 4
    assert m.agent_params.k == 1
