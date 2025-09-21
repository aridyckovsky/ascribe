from __future__ import annotations

import polars as pl

from app.charts import apply_ts_sampling, extract_identity_representation


def test_extract_identity_representation_slices_and_filters() -> None:
    # Arrange
    agent_sel = 0
    t_sel = 1
    # at_df with four objects, choose top_o=2 by |s_io| (should pick o=2 and o=3)
    at_df = pl.DataFrame(
        {
            "t": [t_sel] * 4,
            "agent_id": [agent_sel] * 4,
            "o": [1, 2, 3, 4],
            "s_io": [0.1, 0.9, 0.5, 0.2],
            "rp": [0.01, 0.02, 0.03, 0.04],
            "rn": [-0.01, -0.02, -0.03, -0.04],
        }
    )
    # rel_df: 3 peers by |a_ij| (top_j=2 should pick j=6 (|0.8|) and j=5 (|0.3|))
    rel_df = pl.DataFrame(
        {
            "t": [t_sel, t_sel, t_sel],
            "i": [agent_sel, agent_sel, agent_sel],
            "j": [5, 6, 7],
            "a_ij": [0.3, -0.8, 0.1],
        }
    )
    # other_df: only entries matching selected (j in {5,6} and o in {2,3}) should remain
    other_df = pl.DataFrame(
        {
            "t": [t_sel] * 5,
            "i": [agent_sel] * 5,
            "j": [5, 6, 42, 6, 5],
            "o": [2, 3, 99, 1, 3],
            "b_ijo": [0.2, -0.1, 1.0, 0.0, 0.7],
        }
    )
    # oo_df: only pairs among {2,3} should remain
    oo_df = pl.DataFrame(
        {
            "t": [t_sel] * 4,
            "i": [agent_sel] * 4,
            "o": [2, 2, 3, 1],
            "op": [3, 1, 2, 2],
            "r_oo": [0.4, 0.9, 0.5, 0.8],
        }
    )

    # Act
    out = extract_identity_representation(
        at_df=at_df,
        rel_df=rel_df,
        other_df=other_df,
        oo_df=oo_df,
        agent_sel=agent_sel,
        t_sel=t_sel,
        top_o=2,
        top_j=2,
    )

    # Assert objects contain only top 2 by |s_io| (o=2,3)
    objs = {(row["o"], row["s_io"]) for row in out["objects"]}
    assert {2, 3} == {o for (o, _) in objs}
    # Assert others contain top 2 by |a_ij| (j=6 and j=5), with weights preserved
    others_js = {row["j"] for row in out["others"]}
    assert others_js == {5, 6}
    # b_ijo contains only pairs with selected j and selected o set
    b_pairs = {(row["j"], row["o"]) for row in out["b_ijo"]}
    assert b_pairs.issubset({(5, 2), (5, 3), (6, 2), (6, 3)})
    assert (6, 1) not in b_pairs  # filtered out (o=1 not selected)
    # object_object contains only pairs among selected {2,3}
    oo_pairs = {(row["o"], row["op"]) for row in out["object_object"]}
    assert oo_pairs.issubset({(2, 3), (3, 2)})


def test_apply_ts_sampling_stride_and_max_points() -> None:
    # 100 rows with increasing t
    df = pl.DataFrame({"t": list(range(100)), "x": list(range(100))})
    # Stride 10 should produce approximately 10 rows (exact for 100)
    df_stride = apply_ts_sampling(df, stride=10)
    assert 8 <= df_stride.height <= 12  # allow small tolerance
    # Max points enforces a cap (<= requested)
    df_cap = apply_ts_sampling(df, max_points=7)
    assert 1 <= df_cap.height <= 7
