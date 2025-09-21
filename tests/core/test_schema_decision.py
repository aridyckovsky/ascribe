import pytest
from pydantic import ValidationError

from crv.core.schema import ActionCandidate, DecisionHead


def test_action_candidate_normalizes_action_type() -> None:
    ac = ActionCandidate(
        action_type="acquire_token", parameters={"token_id": "t"}, score=0.5, key="k"
    )
    assert ac.action_type == "acquire_token"


def test_action_candidate_invalid_kind_raises() -> None:
    with pytest.raises(ValidationError):
        # Not lower_snake; grammar requires exact lower_snake tokens
        ActionCandidate(action_type="Acquire_Token", parameters={}, score=0.1, key="k")


def test_decision_head_defaults() -> None:
    dh = DecisionHead()
    assert dh.token_value_estimates == {}
    assert dh.action_candidates == []
    assert dh.abstain is False
    assert dh.temperature == 0.0
