from pathlib import Path

from crv.core.grammar import EBNF_GRAMMAR, PARSED_GRAMMAR, ActionKind, PatchOp


def test_core_ebnf_is_exposed_verbatim() -> None:
    file_text = Path("src/crv/core/core.ebnf").read_text(encoding="utf-8")
    assert EBNF_GRAMMAR == file_text


def test_action_request_matches_enum() -> None:
    assert PARSED_GRAMMAR.lower_snake_terminals("action_request") == tuple(
        member.value for member in ActionKind
    )


def test_patch_edit_matches_enum() -> None:
    assert PARSED_GRAMMAR.lower_snake_terminals("patch_edit") == tuple(
        member.value for member in PatchOp
    )
