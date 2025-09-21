import pytest
from pydantic import ValidationError

from crv.core.schema import MessageRow, ScenarioRow


def test_message_row_visibility_normalization() -> None:
    row = MessageRow(
        tick=0,
        sender_agent_id="a1",
        channel_name="group:G1",
        visibility_scope="PUBLIC",
        audience={"group": "G1"},
        speech_act="say",
        topic_label="t",
    )
    assert row.visibility_scope == "public"


def test_scenario_row_visibility_normalization() -> None:
    row = ScenarioRow(
        tick=1,
        observer_agent_id="obs",
        visibility_scope="gRoUp",
        context_hash="abc",
    )
    assert row.visibility_scope == "group"


def test_visibility_invalid_raises() -> None:
    with pytest.raises(ValidationError):
        MessageRow(
            tick=0,
            sender_agent_id="a1",
            channel_name="room:R",
            visibility_scope="everyone",  # not allowed
            audience={"room": "R"},
            speech_act="say",
            topic_label="t",
        )
