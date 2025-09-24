"""
Canonical CRV grammar and helpers.

Defines actions, channels, visibility scopes, patch operations, representation edge kinds, and exchange kinds. Includes an authoritative lower_snake EBNF and zero-IO validators/helpers used across the stack.

Responsibilities
- Define enums and lower_snake EBNF terminals.
- Provide normalization and validation helpers for enum-like strings and visibility.
- Centralize canonical PatchOp operations (no legacy aliases).
- Supply developer-facing examples and math mapping tables.

Design principles
-----------------
1) One naming standard:
   - Enum classes: PascalCase
   - Enum member names: UPPER_SNAKE (Python constants)
   - Enum serialized values (wire/EBNF/Parquet): lower_snake
   - Fields & columns elsewhere: lower_snake

2) Psychology-first:
   - Core grammar does NOT encode legal “rights” taxonomies.
   - Exchanges are generic and MAY publish a baseline_value that can feed
     valuation V(token) as B_token(t). Venue-specific mechanics live in
     payloads, not in core enums.

3) Representation vs. topology:
   - RepresentationEdgeKind describes edges INSIDE an agent's identity/
     affect representation and is logged to identity_edges.
   - TopologyEdgeKind (optional/future) describes links in the WORLD
     topology (e.g., “is_neighbor”, “follows”) and would be logged to a
     separate world_topology_edges table if/when you add it.

Math-to-Code mapping
-----------------------------------
The code intentionally avoids math symbols; this mapping aids researchers. Edge rows use RepresentationEdgeKind values (edge_kind) in identity_edges; readout/valuation/baseline remain field names.

| Math symbol                      | Meaning (concept)                                       | Code enum/value
|----------------------------------|---------------------------------------------------------|-----------------------------
| s^+_{agent}                      | self positive anchor                                    | self_to_positive_valence
| s^-_{agent}                      | self negative anchor                                    | self_to_negative_valence
| s_{agent,token}                  | self→object attachment (endowment)                      | self_to_object
| a_{agent,other_agent}            | primitive self→other attitude                           | self_to_agent
| u^+_{agent,other_agent}          | positive feeling toward other agent                     | agent_to_positive_valence
| u^-_{agent,other_agent}          | negative feeling toward other agent                     | agent_to_negative_valence
| b_{agent,other_agent,token}      | other→object stance (as perceived by self)              | agent_to_object
| d_{agent,other_a,other_b}        | other–other alliance/rivalry (as perceived)             | agent_to_agent
| q_{agent,other_a,other_b,token}  | pair-on-object (perceived coalition on token)           | agent_pair_to_object
| r^+_{agent,token}                | positive object trace                                   | object_to_positive_valence
| r^-_{agent,token}                | negative object trace                                   | object_to_negative_valence
| c_{agent,token_a,token_b}        | token–token association                                 | object_to_object
| U_agent(token)                   | representation readout driver                           | representation_score
| V_agent(token)                   | bounded valuation                                       | valuation_score
| B_token(t)                       | exchange baseline (price/poll/trend)                    | baseline_value

Downstream usage
----------------
- Validators across `crv.core.schema` call these helpers to normalize and guard
  enum-like strings (e.g., `action_kind_from_value`, `exchange_kind_from_value`,
  `edge_kind_from_value`, `normalize_visibility`).
- Tests and dashboards use `ensure_all_enum_values_lower_snake` to enforce
  naming invariants.
- `canonical_action_key` provides compact, human-friendly labels for logs and
  dashboards; program logic MUST NOT parse it (use structured fields instead).

Examples
--------
Normalize visibility and action kinds, and build a canonical key:

>>> from crv.core.grammar import (
...     normalize_visibility,
...     action_kind_from_value,
...     canonical_action_key,
...     ActionKind,
... )
>>> normalize_visibility("PUBLIC")
'public'
>>> action_kind_from_value("acquire_token") == ActionKind.ACQUIRE_TOKEN
True
>>> canonical_action_key(ActionKind.ACQUIRE_TOKEN, token_id="Alpha")
'acquire_token:token_id=Alpha'

Tags
----
grammar, enums, normalization, ebnf, lower_snake, helpers
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

__all__ = [
    "ActionKind",
    "ChannelType",
    "Visibility",
    "PatchOp",
    "RepresentationEdgeKind",
    "TopologyEdgeKind",
    "ExchangeKind",
    "TableName",
    "EBNF_GRAMMAR",
    "GrammarProduction",
    "ParsedGrammar",
    "PARSED_GRAMMAR",
    # helpers/validators
    "is_lower_snake",
    "assert_lower_snake",
    "action_value",
    "action_kind_from_value",
    "exchange_value",
    "exchange_kind_from_value",
    "edge_value",
    "edge_kind_from_value",
    "normalize_visibility",
    "normalize_channel_type",
    "canonical_action_key",
    "ensure_all_enum_values_lower_snake",
]

# Canonical grammar file next to this module
_EBNF_PATH = Path(__file__).with_name("core.ebnf")


def _load_ebnf_text() -> str:
    # Return the canonical EBNF text (no normalization).
    return _EBNF_PATH.read_text(encoding="utf-8")


EBNF_GRAMMAR: Final[str] = _load_ebnf_text()


@dataclass(slots=True, frozen=True)
class GrammarProduction:
    """Parsed production with convenient accessors."""

    name: str
    expression: str
    alternatives: tuple[str, ...]
    leading_terminals: tuple[str, ...]

    def lower_snake_terminals(self) -> tuple[str, ...]:
        return tuple(token for token in self.leading_terminals if is_lower_snake(token))


@dataclass(slots=True, frozen=True)
class ParsedGrammar:
    """Container for parsed grammar productions."""

    productions: dict[str, GrammarProduction]

    def production(self, name: str) -> GrammarProduction:
        try:
            return self.productions[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown grammar production: {name}") from exc

    def lower_snake_terminals(self, name: str) -> tuple[str, ...]:
        return self.production(name).lower_snake_terminals()

    @classmethod
    def from_text(cls, text: str) -> ParsedGrammar:
        stripped = _strip_ebnf_comments(text)
        productions: dict[str, GrammarProduction] = {}
        for match in _RULE_RE.finditer(stripped):
            rule_name = match.group(1)
            expression = match.group(2).strip()
            alternatives = _split_alternatives(expression)
            leading = tuple(
                literal
                for literal in (_first_literal(part) for part in alternatives)
                if literal is not None
            )
            productions[rule_name] = GrammarProduction(
                name=rule_name,
                expression=expression,
                alternatives=alternatives,
                leading_terminals=_dedupe_preserving_order(leading),
            )
        return cls(productions=productions)


_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
_RULE_RE = re.compile(r"(?ms)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*;")
_LITERAL_RE = re.compile(r"[\"']([^\"']+)[\"']")


def _strip_ebnf_comments(text: str) -> str:
    return _COMMENT_RE.sub(" ", text)


def _split_alternatives(expression: str) -> tuple[str, ...]:
    parts: list[str] = []
    buffer: list[str] = []
    depth = 0
    quote: str | None = None
    i = 0
    while i < len(expression):
        ch = expression[i]
        if quote is not None:
            buffer.append(ch)
            if ch == quote:
                quote = None
            elif ch == "\\" and i + 1 < len(expression):
                i += 1
                buffer.append(expression[i])
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            buffer.append(ch)
        elif ch in "([{":
            depth += 1
            buffer.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            buffer.append(ch)
        elif ch == "|" and depth == 0:
            part = "".join(buffer).strip()
            if part:
                parts.append(part)
            buffer = []
        else:
            buffer.append(ch)
        i += 1
    tail = "".join(buffer).strip()
    if tail:
        parts.append(tail)
    return tuple(parts)


def _first_literal(alt: str) -> str | None:
    match = _LITERAL_RE.search(alt)
    return match.group(1) if match else None


def _dedupe_preserving_order(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)


# ============================================================================
# ACTIONS, CHANNELS, VISIBILITY
# ============================================================================


class ActionKind(Enum):
    """
    All concrete action verbs an agent (or venue) may emit.

    Serialized values are used in:
      - DecisionHead.action_candidates[].action_type (schema.DecisionHead)
      - Event envelopes payloads written by world
      - EBNF terminals

    Notes:
      Table mappings:
        * messages           (send_chat_message, publish_announcement)
        * exchange           (post/cancel/order, trade, swap, peer exchange, vote, gift)
        * scenarios_seen     (as part of context reconstruction)
        * decisions          (chosen_action and action_candidates)
    """

    ACQUIRE_TOKEN = "acquire_token"
    RELINQUISH_TOKEN = "relinquish_token"
    RELATE_AGENT = "relate_agent"
    RELATE_OTHER_AGENTS = "relate_other_agents"
    ENDORSE_TOKEN = "endorse_token"
    COENDORSE_TOKEN_WITH_AGENTS = "coendorse_token_with_agents"
    EXPOSE_SIGNAL_ABOUT_TOKEN = "expose_signal_about_token"
    DECLARE_COOCCURRENCE = "declare_cooccurrence_between_tokens"

    PROPOSE_PEER_EXCHANGE = "propose_peer_exchange"
    ACCEPT_PEER_EXCHANGE = "accept_peer_exchange"
    REJECT_PEER_EXCHANGE = "reject_peer_exchange"
    SETTLE_PEER_EXCHANGE = "settle_peer_exchange"

    POST_ORDER_TO_VENUE = "post_order_to_venue"
    CANCEL_ORDER_AT_VENUE = "cancel_order_at_venue"
    SETTLE_TRADE_FROM_VENUE = "settle_trade_from_venue"
    SWAP_AT_VENUE = "swap_at_venue"

    CAST_VOTE_AT_VENUE = "cast_vote_at_venue"
    PUBLISH_VOTE_OUTCOME = "publish_vote_outcome_from_venue"
    GIFT_TOKEN = "gift_token"

    SEND_CHAT_MESSAGE = "send_chat_message"
    PUBLISH_ANNOUNCEMENT = "publish_announcement"


class ChannelType(Enum):
    """
    Logical channel families for routing & visibility.

    Serialized values appear in:
      - messages.channel_name (prefix like 'group:G1', 'room:market')
      - event envelopes channel field
    """

    PUBLIC = "public"
    GROUP = "group"
    ROOM = "room"
    DM = "dm"


class Visibility(Enum):
    """
    Rendered visibility on observations or messages.

    Serialized values appear in:
      - messages.visibility_scope
      - event envelopes visibility field
      - scenarios_seen.visibility_scope
    """

    PUBLIC = "public"
    GROUP = "group"
    ROOM = "room"
    DM = "dm"


# ============================================================================
# REPRESENTATION PATCH OPERATIONS (AGENT'S INTERNAL STATE)
# ============================================================================


class PatchOp(Enum):
    """
    Atomic edit operations over the identity/affect representation.

    Canonical-only policy:
      Only the following operations are valid and accepted:
        - set_identity_edge_weight
        - adjust_identity_edge_weight
        - decay_identity_edges
        - remove_identity_edge

    Notes:
      Use the canonical operations together with explicit edge_kind and fields, e.g.,
      object_to_object with subject_id/object_id, or object_to_positive_valence /
      object_to_negative_valence with token_id.

      Table mappings:
        * identity_edges (rows produced AFTER patches are applied) — we log the
          post-barrier state, not the patch instruction itself.
    """

    SET_IDENTITY_EDGE_WEIGHT = "set_identity_edge_weight"
    ADJUST_IDENTITY_EDGE_WEIGHT = "adjust_identity_edge_weight"
    DECAY_IDENTITY_EDGES = "decay_identity_edges"
    REMOVE_IDENTITY_EDGE = "remove_identity_edge"


class RepresentationEdgeKind(Enum):
    """
    Identity/affect edge kinds INSIDE an agent's representation.

    Use these values in:
      - identity_edges.edge_kind

    Notes:
      Table mappings:
        * identity_edges: one row per edge snapshot/delta written AFTER the
          barrier applies representation patches.

      Psych/math mapping:
        These correspond to the following psychological constructs and math symbols.
        Valence is modeled as dual implicit channels per object (r^+_{i,o}, r^-_{i,o}) and dual "friend/foe" channels per other agent (u^+_{i,j}, u^-_{i,j}) from self i's perspective. a_{i,j} is an additional primitive self–other tie; anchors s_i^+, s_i^- are slow self-evaluations.

          - self_to_positive_valence      -> s^+_{i}            (self anchor)
          - self_to_negative_valence      -> s^-_{i}            (self anchor)
          - self_to_object                -> s_{i,o}
          - self_to_agent                 -> a_{i,j}            (primitive self–other tie)
          - agent_to_positive_valence     -> u^+_{i,j}          (self's positive feeling toward agent j)
          - agent_to_negative_valence     -> u^-_{i,j}          (self's negative feeling toward agent j)
          - agent_to_object               -> b_{i,j,o}
          - agent_to_agent                -> d_{i,k,l}
          - agent_pair_to_object          -> q_{i,k,l,o}
          - object_to_positive_valence    -> r^+_{i,o}
          - object_to_negative_valence    -> r^-_{i,o}
          - object_to_object              -> c_{i,o,o'}
    """

    SELF_TO_POSITIVE_VALENCE = "self_to_positive_valence"
    SELF_TO_NEGATIVE_VALENCE = "self_to_negative_valence"
    SELF_TO_OBJECT = "self_to_object"
    SELF_TO_AGENT = "self_to_agent"
    AGENT_TO_POSITIVE_VALENCE = "agent_to_positive_valence"
    AGENT_TO_NEGATIVE_VALENCE = "agent_to_negative_valence"
    AGENT_TO_OBJECT = "agent_to_object"
    AGENT_TO_AGENT = "agent_to_agent"
    AGENT_PAIR_TO_OBJECT = "agent_pair_to_object"
    OBJECT_TO_POSITIVE_VALENCE = "object_to_positive_valence"
    OBJECT_TO_NEGATIVE_VALENCE = "object_to_negative_valence"
    OBJECT_TO_OBJECT = "object_to_object"


class TopologyEdgeKind(Enum):
    """
    World topology edge kinds (STRUCTURE OUTSIDE the agent).

    These DO NOT go into identity_edges. In a topology/world table,
    use these values for that table's edge_kind (e.g., 'world_topology_edges').

    Examples:
      - is_neighbor: grid/graph adjacency
      - follows: directed social following
      - in_group: static group membership edge

    Notes:
      Table mappings:
        * world_topology_edges (future) — NOT part of identity_edges.
    """

    IS_NEIGHBOR = "is_neighbor"
    FOLLOWS = "follows"
    IN_GROUP = "in_group"
    CONNECTS_ROOM = "connects_room"


# ============================================================================
# EXCHANGE EVENT KINDS (GENERALIZED MARKET)
# ============================================================================


class ExchangeKind(Enum):
    """
    Generalized ownership-exchange events (beyond finance).

    Serialized values appear in:
      - exchange.exchange_event_type
      - EBNF terminals in the 'exchange' section

    Notes:
      Table mappings:
        * exchange (one row per event):
            - price/quantity for trade-like events
            - baseline_value if venue emits an index (price / poll % / trend)
            - additional_payload for venue specifics
    """

    TRADE = "trade"
    ORDER_POST = "order_post"
    ORDER_CANCEL = "order_cancel"
    SWAP = "swap"
    GIFT = "gift"
    PEER_OFFER = "peer_offer"
    PEER_ACCEPT = "peer_accept"
    PEER_REJECT = "peer_reject"
    CAST_VOTE = "cast_vote"
    VOTE_OUTCOME = "vote_outcome"


# ============================================================================
# TABLE NAMES (LOWER_SNAKE)
# ============================================================================


class TableName(Enum):
    """
    Canonical Parquet table names. Enforced by crv.io.tables.
    """

    EXCHANGE = "exchange"
    IDENTITY_EDGES = "identity_edges"
    SCENARIOS_SEEN = "scenarios_seen"
    MESSAGES = "messages"
    DECISIONS = "decisions"
    ORACLE_CALLS = "oracle_calls"
    HOLDINGS = "holdings"
    HOLDINGS_VALUATION = "holdings_valuation"


# ============================================================================
# Helpers & Validators (zero I/O)
# ============================================================================

_LOWER_SNAKE_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def is_lower_snake(value: str) -> bool:
    """
    Check whether a string is lower_snake.

    Args:
      value (str): Candidate string to validate.

    Returns:
      bool: True if value matches lower_snake (e.g., "acquire_token"), False otherwise.

    Examples:
      >>> is_lower_snake("acquire_token")
      True
      >>> is_lower_snake("AcquireToken")
      False
    """
    return bool(_LOWER_SNAKE_RE.match(value or ""))


def assert_lower_snake(value: str, what: str = "value") -> None:
    """
    Validate that a string is lower_snake.

    Args:
      value (str): Candidate string to validate.
      what (str): Human-friendly label used in the error message.

    Raises:
      ValueError: If value is not lower_snake.
    """
    if not is_lower_snake(value):
        raise ValueError(f"{what} must be lower_snake (got: {value!r})")


def action_value(kind: ActionKind) -> str:
    """
    Get the serialized (lower_snake) value for an ActionKind.

    Args:
      kind (ActionKind): Action enum.

    Returns:
      str: Lower_snake serialized value (e.g., "acquire_token").
    """
    return kind.value


def action_kind_from_value(s: str) -> ActionKind:
    """
    Parse a lower_snake action string into an ActionKind.

    Args:
      s (str): Lower_snake action string.

    Returns:
      ActionKind: Parsed action kind.

    Raises:
      ValueError: If s is not lower_snake or is not a known action.
    """
    assert_lower_snake(s, "action_type")
    return ActionKind(s)


def exchange_value(kind: ExchangeKind) -> str:
    """
    Get the serialized (lower_snake) value for an ExchangeKind.

    Args:
      kind (ExchangeKind): Exchange enum.

    Returns:
      str: Lower_snake serialized value (e.g., "trade").
    """
    return kind.value


def exchange_kind_from_value(s: str) -> ExchangeKind:
    """
    Parse a lower_snake exchange string into an ExchangeKind.

    Args:
      s (str): Lower_snake exchange kind string.

    Returns:
      ExchangeKind: Parsed exchange kind.

    Raises:
      ValueError: If s is not lower_snake or is not a known exchange kind.
    """
    assert_lower_snake(s, "exchange_event_type")
    return ExchangeKind(s)


def edge_value(kind: RepresentationEdgeKind) -> str:
    """
    Get the serialized (lower_snake) value for a RepresentationEdgeKind.

    Args:
      kind (RepresentationEdgeKind): Edge kind enum.

    Returns:
      str: Lower_snake serialized value (e.g., "object_to_object").
    """
    return kind.value


def edge_kind_from_value(s: str) -> RepresentationEdgeKind:
    """
    Parse a lower_snake edge_kind string into a RepresentationEdgeKind.

    Args:
      s (str): Lower_snake edge kind string.

    Returns:
      RepresentationEdgeKind: Parsed edge kind.

    Raises:
      ValueError: If s is not lower_snake or is not a known edge kind.
    """
    assert_lower_snake(s, "edge_kind")
    return RepresentationEdgeKind(s)


def normalize_visibility(vis: str) -> str:
    """
    Normalize a free-form visibility token to canonical lower_snake.

    Args:
      vis (str): Candidate visibility token.

    Returns:
      str: One of {"public","group","room","dm"}.

    Raises:
      ValueError: If the token does not match a known visibility class.

    Notes:
      Used by:
        - messages.visibility_scope
        - scenarios_seen.visibility_scope
        - event envelopes visibility field
    """
    vis_l = (vis or "").lower()
    allowed = {v.value for v in Visibility}
    if vis_l not in allowed:
        raise ValueError(f"visibility must be one of {sorted(allowed)} (got {vis!r})")
    return vis_l


def normalize_channel_type(ch: str) -> str:
    """
    Normalize a free-form channel type token to canonical lower_snake.

    Args:
      ch (str): Candidate channel type token.

    Returns:
      str: One of {"public","group","room","dm"}.

    Raises:
      ValueError: If the token is not a recognized channel type.

    Notes:
      Typically used only for validation when parsing a channel prefix.
    """
    ch_l = (ch or "").lower()
    allowed = {c.value for c in ChannelType}
    if ch_l not in allowed:
        raise ValueError(f"channel type must be one of {sorted(allowed)} (got {ch!r})")
    return ch_l


def canonical_action_key(action_type: ActionKind, **params: object) -> str:
    """
    Build a compact, human-friendly log key for an action candidate.

    Args:
      action_type (ActionKind): Action type to label.
      **params (object): Optional parameters to include in the label.

    Returns:
      str: Key formatted as "action:sorted_k=v|k=v".

    Examples:
      >>> canonical_action_key(ActionKind.ACQUIRE_TOKEN, token_id="Alpha")
      'acquire_token:token_id=Alpha'
      >>> canonical_action_key(ActionKind.SEND_CHAT_MESSAGE, channel="group:G1")
      'send_chat_message:channel=group:G1'

    Notes:
      The key is for logs and dashboards only; program logic must use
      structured fields rather than parsing this string.

      Used by:
        - decisions.action_candidates[].key (string)
        - logs / dashboards (viz) as human-readable labels
    """
    parts = [action_type.value]
    if params:
        ordered = ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
        parts.append(ordered.replace(", ", "|"))
    return ":".join(parts)


def ensure_all_enum_values_lower_snake(enums: Iterable[type[Enum]]) -> None:
    """
    Assert that every enum member's value is lower_snake.

    Args:
      enums (Iterable[type[Enum]]): Iterable of Enum classes to inspect.

    Raises:
      AssertionError: If any enum member has a non-lower_snake value.

    Examples:
      >>> ensure_all_enum_values_lower_snake([
      ...     ActionKind, ChannelType, Visibility,
      ...     PatchOp, RepresentationEdgeKind, ExchangeKind, TableName
      ... ])
    """
    for E in enums:
        for m in E:
            if not is_lower_snake(m.value):
                raise AssertionError(
                    f"{E.__name__}.{m.name} has non-lower_snake value: {m.value!r}"
                )


def _assert_production_matches_enum(
    grammar: ParsedGrammar, rule_name: str, enum_cls: type[Enum]
) -> None:
    actual = list(grammar.lower_snake_terminals(rule_name))
    expected = [member.value for member in enum_cls]
    if actual != expected:
        actual_set = set(actual)
        expected_set = set(expected)
        issues: list[str] = []
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        if missing:
            issues.append(f"missing {sorted(missing)}")
        if extra:
            issues.append(f"unexpected {sorted(extra)}")
        if not issues:
            issues.append("ordering differs")
        raise ValueError(
            f"Grammar production {rule_name!r} out of sync with {enum_cls.__name__}: "
            + "; ".join(issues)
        )


PARSED_GRAMMAR: Final[ParsedGrammar] = ParsedGrammar.from_text(EBNF_GRAMMAR)
_assert_production_matches_enum(PARSED_GRAMMAR, "action_request", ActionKind)
_assert_production_matches_enum(PARSED_GRAMMAR, "patch_edit", PatchOp)
