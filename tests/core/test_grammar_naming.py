from crv.core.grammar import (
    ActionKind,
    ChannelType,
    ExchangeKind,
    PatchOp,
    RepresentationEdgeKind,
    TableName,
    Visibility,
    ensure_all_enum_values_lower_snake,
)


def test_all_enum_values_are_lower_snake() -> None:
    ensure_all_enum_values_lower_snake(
        [
            ActionKind,
            ChannelType,
            Visibility,
            PatchOp,
            RepresentationEdgeKind,
            ExchangeKind,
            TableName,
        ]
    )
