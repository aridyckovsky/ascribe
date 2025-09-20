import pytest
from pydantic import ValidationError

from crv.core.schema import GraphEdit


def test_graphedit_accepts_canonical_ops_token_token() -> None:
    # Token–token association via verbose grammar
    ge = GraphEdit(
        operation="set_identity_edge_weight",
        edge_kind="object_to_object",
        subject_id="TokenA",
        object_id="TokenB",
        new_weight=0.75,
    )
    assert ge.operation == "set_identity_edge_weight"
    assert ge.edge_kind == "object_to_object"
    assert ge.subject_id == "TokenA"
    assert ge.object_id == "TokenB"
    assert ge.new_weight == 0.75


@pytest.mark.parametrize(
    "edge_kind,delta",
    [
        ("object_to_positive_valence", 0.10),
        ("object_to_negative_valence", -0.05),
    ],
)
def test_graphedit_accepts_valence_traces(edge_kind: str, delta: float) -> None:
    ge = GraphEdit(
        operation="adjust_identity_edge_weight",
        edge_kind=edge_kind,
        token_id="TokenX",
        delta_weight=delta,
    )
    assert ge.operation == "adjust_identity_edge_weight"
    assert ge.edge_kind == edge_kind
    assert ge.token_id == "TokenX"
    assert ge.delta_weight == delta


def test_graphedit_accepts_decay_operation() -> None:
    ge = GraphEdit(
        operation="decay_identity_edges",
        edge_kind="object_to_object",
        scope_selector="all",
        decay_lambda=0.9,
    )
    assert ge.operation == "decay_identity_edges"
    assert ge.edge_kind == "object_to_object"
    assert ge.scope_selector == "all"
    assert ge.decay_lambda == 0.9


@pytest.mark.parametrize(
    "legacy_op",
    [
        "set_identity_edge_weight_o2o",
        "adjust_identity_edge_weight_o2o",
        "adjust_identity_edge_weight_o2o_object",
    ],
)
def test_graphedit_rejects_legacy_o2o_ops(legacy_op: str) -> None:
    with pytest.raises(ValidationError):
        GraphEdit(
            operation=legacy_op,
            edge_kind="object_to_object",
            subject_id="A",
            object_id="B",
            new_weight=0.1,
        )


@pytest.mark.parametrize(
    "bad_op",
    [
        "Set_Identity_Edge_Weight",  # not lower_snake
        "unknown_operation_kind",  # not in canonical set
    ],
)
def test_graphedit_rejects_non_lower_snake_and_unknown(bad_op: str) -> None:
    with pytest.raises(ValidationError):
        GraphEdit(
            operation=bad_op,
            edge_kind="object_to_object",
            subject_id="A",
            object_id="B",
            new_weight=0.2,
        )


def test_graphedit_accepts_agent_valence_channel_positive() -> None:
    ge = GraphEdit(
        operation="adjust_identity_edge_weight",
        edge_kind="agent_to_positive_valence",
        subject_id="AgentJ",
        delta_weight=0.2,
    )
    assert ge.operation == "adjust_identity_edge_weight"
    assert ge.edge_kind == "agent_to_positive_valence"
    assert ge.subject_id == "AgentJ"
    assert ge.delta_weight == 0.2


def test_graphedit_accepts_self_anchor_positive() -> None:
    ge = GraphEdit(
        operation="set_identity_edge_weight",
        edge_kind="self_to_positive_valence",
        new_weight=0.8,
    )
    assert ge.operation == "set_identity_edge_weight"
    assert ge.edge_kind == "self_to_positive_valence"
    assert ge.new_weight == 0.8
