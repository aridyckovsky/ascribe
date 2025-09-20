from typing import Any

import pytest
from pydantic import ValidationError

from crv.core.errors import SchemaError
from crv.core.schema import IdentityEdgeRow

# Matrix of required field combos per edge_kind
REQUIRED_BY_KIND: dict[str, set[str]] = {
    "self_to_positive_valence": set(),
    "self_to_negative_valence": set(),
    "self_to_object": {"subject_id", "token_id"},
    "self_to_agent": {"subject_id", "object_id"},
    "agent_to_positive_valence": {"subject_id"},
    "agent_to_negative_valence": {"subject_id"},
    "agent_to_object": {"subject_id", "token_id"},
    "agent_to_agent": {"subject_id", "object_id"},
    "agent_pair_to_object": {"subject_id", "related_agent_id", "token_id"},
    "object_to_positive_valence": {"token_id"},
    "object_to_negative_valence": {"token_id"},
    "object_to_object": {"subject_id", "object_id"},
}


def make_minimal_payload(kind: str) -> dict[str, Any]:
    base = dict(tick=0, observer_agent_id="agent_a", edge_kind=kind, edge_weight=0.5)
    required = REQUIRED_BY_KIND[kind]
    # Fill in minimal required fields with dummy strings
    for field in required:
        base[field] = "X"
    return base


@pytest.mark.parametrize("kind", sorted(REQUIRED_BY_KIND.keys()))
def test_identity_edge_row_positive_minimal(kind: str) -> None:
    payload = make_minimal_payload(kind)
    row = IdentityEdgeRow(**payload)
    assert row.edge_kind == kind
    # Ensure all required fields exist and non-empty
    for field in REQUIRED_BY_KIND[kind]:
        assert getattr(row, field)


@pytest.mark.parametrize("kind", sorted(REQUIRED_BY_KIND.keys()))
def test_identity_edge_row_missing_each_required_field(kind: str) -> None:
    required = REQUIRED_BY_KIND[kind]
    for missing in required:
        payload = make_minimal_payload(kind)
        payload.pop(missing, None)
        with pytest.raises(ValidationError) as ei:
            IdentityEdgeRow(**payload)
        # Bubble-up comes as ValidationError; inner cause should be SchemaError message
        assert any(
            isinstance(err, SchemaError) or "requires fields" in str(err)
            for err in ei.value.errors()
        )
