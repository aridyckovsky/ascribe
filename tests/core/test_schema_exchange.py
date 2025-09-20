import pytest
from pydantic import ValidationError

from src.crv.core.schema import ExchangeRow


def test_exchange_kind_accepts_lower_snake() -> None:
    row = ExchangeRow(tick=0, venue_id="v1", token_id="t1", exchange_event_type="trade")
    assert row.exchange_event_type == "trade"


def test_exchange_kind_invalid_raises() -> None:
    with pytest.raises(ValidationError):
        ExchangeRow(tick=0, venue_id="v1", token_id="t1", exchange_event_type="not_a_kind")


def test_side_normalization_case_insensitive() -> None:
    row = ExchangeRow(
        tick=1,
        venue_id="v1",
        token_id="t1",
        exchange_event_type="trade",
        side="BUY",
    )
    assert row.side == "buy"
