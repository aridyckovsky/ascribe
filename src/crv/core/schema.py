"""
Pydantic v2 models for core payloads, decisions, context/persona/affect, and row
schemas. Validators normalize fields to canonical lower_snake using grammar helpers and
enforce cross-field combination rules (notably for identity_edges).

Responsibilities
- Define the canonical Pydantic models for payloads, decisions, context/persona/affect, and rows.
- Normalize enum-like strings to lower_snake via grammar helpers.
- Enforce cross-field combination rules and value ranges (e.g., IdentityEdgeRow).
- Provide docstrings with Table mappings and, where applicable, Math mapping examples.

Style
- Zero-IO (stdlib + pydantic only).
- Google-style docstrings with sections such as Attributes, Args, Returns, Raises, Examples, and Notes.
- Row models include “Table mappings” and, where relevant, a “Math mapping” under Notes.

References
- specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
- grammar: src/crv/core/grammar.py (enums, EBNF, normalization helpers)
- errors: src/crv/core/errors.py (SchemaError, GrammarError)
- tests: tests/core/*
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .errors import GrammarError, SchemaError
from .grammar import (
    action_kind_from_value,
    edge_kind_from_value,
    exchange_kind_from_value,
    is_lower_snake,
    normalize_visibility,
)
from .typing import JsonDict

__all__ = [
    # Payloads
    "Utterance",
    "Interpretation",
    "AppraisalVector",
    "GraphEdit",
    "RepresentationPatch",
    # Decisions
    "ActionCandidate",
    "DecisionHead",
    # Context / Persona / Affect
    "ScenarioContext",
    "Persona",
    "AffectState",
    # Rows (tables)
    "EventEnvelopeRow",
    "MessageRow",
    "ExchangeRow",
    "IdentityEdgeRow",
    "ScenarioRow",
    "DecisionRow",
    "OracleCallRow",
]

# ============================================================================
# Payloads
# ============================================================================


class Utterance(BaseModel):
    """
    Textual utterance structure used by messaging channels.

    Attributes:
        act (str): Speech act label.
        topic (str): Topic label.
        stance (str | None): Optional stance label.
        claims (list[dict[str, Any]]): Structured claim list (free-form schema).
        style (dict[str, Any]): Rendering or rhetorical style.
        audience (list[str]): Target audience hints.

    Notes:
        Field names are lower_snake; free-form strings are kept verbatim.

    Examples:
        >>> from crv.core.schema import Utterance
        >>> Utterance(act="say", topic="token_alpha", stance=None)
    """

    model_config = ConfigDict(extra="forbid")

    act: str
    topic: str
    stance: str | None = None
    claims: list[dict[str, Any]] = Field(default_factory=list)
    style: dict[str, Any] = Field(default_factory=dict)
    audience: list[str] = Field(default_factory=list)


class Interpretation(BaseModel):
    """
    Agent’s interpretation of an event.

    Attributes:
        event_type (str): Interpreted event kind label.
        targets (list[str]): Target identifiers (agents/tokens).
        inferred (dict[str, Any]): Derived attributes (free-form).
        salience (float): Perceived salience in [0, 1].

    Raises:
        pydantic.ValidationError: If salience is outside [0, 1].

    Examples:
        >>> from crv.core.schema import Interpretation
        >>> Interpretation(event_type="endorsement", targets=["agent_j"], salience=0.7)
    """

    model_config = ConfigDict(extra="forbid")

    event_type: str
    targets: list[str] = Field(default_factory=list)
    inferred: dict[str, Any] = Field(default_factory=dict)
    salience: float = Field(..., ge=0.0, le=1.0)


class AppraisalVector(BaseModel):
    """
    Psychological appraisals used by value readout.

    Attributes:
        valence (float): In [0, 1].
        arousal (float): In [0, 1].
        certainty (float): In [0, 1].
        novelty (float): In [0, 1].
        goal_congruence (float): In [0, 1].

    Notes:
        Components correspond to scalar channels used in bounded valuation V(token).

    Raises:
        pydantic.ValidationError: If any component is outside [0, 1].
    """

    model_config = ConfigDict(extra="forbid")

    valence: float = Field(..., ge=0.0, le=1.0)
    arousal: float = Field(..., ge=0.0, le=1.0)
    certainty: float = Field(..., ge=0.0, le=1.0)
    novelty: float = Field(..., ge=0.0, le=1.0)
    goal_congruence: float = Field(..., ge=0.0, le=1.0)


_ALLOWED_GRAPH_OPS: set[str] = {
    "set_identity_edge_weight",
    "adjust_identity_edge_weight",
    "decay_identity_edges",
    "remove_identity_edge",
}


class GraphEdit(BaseModel):
    """
    Canonical graph edit instruction applied to the agent's identity/affect representation.

    Attributes:
        operation (str): One of:
            {"set_identity_edge_weight","adjust_identity_edge_weight","decay_identity_edges","remove_identity_edge"}.
        edge_kind (str): RepresentationEdgeKind serialized value (lower_snake).
        subject_id (str | None): Subject agent identifier (when applicable).
        object_id (str | None): Object/other agent identifier (when applicable).
        related_agent_id (str | None): Related agent identifier for agent-pair cases.
        token_id (str | None): Token identifier (when applicable).
        new_weight (float | None): New weight for set operations.
        delta_weight (float | None): Delta for adjust operations.
        scope_selector (str | None): Selector used for decay scope (implementation-defined).
        decay_lambda (float | None): Decay factor in [0, 1].

    Raises:
        crv.core.errors.GrammarError: If operation or edge_kind is invalid or not lower_snake.
        pydantic.ValidationError: If decay_lambda is outside [0, 1].

    Examples:
        - Token–token association:
          {"operation": "set_identity_edge_weight", "edge_kind": "object_to_object",
           "subject_id": "TokenA", "object_id": "TokenB", "new_weight": 0.75}
        - Positive valence trace:
          {"operation": "adjust_identity_edge_weight", "edge_kind": "object_to_positive_valence",
           "token_id": "TokenX", "delta_weight": 0.10}
        - Negative valence trace:
          {"operation": "adjust_identity_edge_weight", "edge_kind": "object_to_negative_valence",
           "token_id": "TokenX", "delta_weight": -0.05}
        - Agent friend channel (positive):
          {"operation": "adjust_identity_edge_weight", "edge_kind": "agent_to_positive_valence",
           "subject_id": "AgentJ", "delta_weight": 0.20}
        - Self positive anchor:
          {"operation": "set_identity_edge_weight", "edge_kind": "self_to_positive_valence",
           "new_weight": 0.80}
    """

    model_config = ConfigDict(extra="forbid")

    operation: str
    edge_kind: str
    subject_id: str | None = None
    object_id: str | None = None
    related_agent_id: str | None = None
    token_id: str | None = None
    new_weight: float | None = None
    delta_weight: float | None = None
    scope_selector: str | None = None
    decay_lambda: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("operation", mode="before")
    @classmethod
    def _check_operation(cls, v: Any) -> str:
        """
        Validate that GraphEdit.operation is lower_snake and canonical.

        Args:
            v (Any): Proposed operation string.

        Returns:
            str: Canonical lower_snake operation string.

        Raises:
            GrammarError: If not lower_snake or not in the allowed set.
        """
        s = v or ""
        if not is_lower_snake(s):
            raise GrammarError(f"graph operation must be lower_snake, got {v!r}")
        if s not in _ALLOWED_GRAPH_OPS:
            raise GrammarError(f"unknown graph operation {v!r}")
        return s

    @field_validator("edge_kind", mode="before")
    @classmethod
    def _normalize_edge_kind(cls, v: Any) -> Any:
        """
        Normalize edge_kind using grammar.edge_kind_from_value.

        Args:
            v (Any): Proposed edge_kind string.

        Returns:
            Any: Canonical lower_snake edge_kind string, or None.

        Raises:
            GrammarError: If not lower_snake or unknown edge kind.
        """
        if v is None:
            return v
        try:
            return edge_kind_from_value(str(v)).value
        except Exception as e:  # ValueError from grammar
            raise GrammarError(str(e)) from e


class RepresentationPatch(BaseModel):
    """
    Container for graph edits applied at the t+1 barrier.

    Attributes:
        edits (list[GraphEdit]): Ordered list of canonical graph edits.
        energy_delta (float | None): Optional diagnostic indicating BIT energy change.

    Notes:
        Groups canonical GraphEdit operations that, when applied by the world barrier,
        mutate the unified identity/affect representation.

    Examples:
        >>> from crv.core.schema import GraphEdit, RepresentationPatch
        >>> patch = RepresentationPatch(
        ...     edits=[
        ...         GraphEdit(operation="set_identity_edge_weight",
        ...                  edge_kind="object_to_object",
        ...                  subject_id="TokenA", object_id="TokenB",
        ...                  new_weight=0.75),
        ...         GraphEdit(operation="adjust_identity_edge_weight",
        ...                  edge_kind="object_to_positive_valence",
        ...                  token_id="Alpha", delta_weight=0.1),
        ...     ]
        ... )
        >>> len(patch.edits)
        2
    """

    model_config = ConfigDict(extra="forbid")

    edits: list[GraphEdit] = Field(default_factory=list)
    energy_delta: float | None = None


# ============================================================================
# Decisions
# ============================================================================


class ActionCandidate(BaseModel):
    """
    One scored action option with explicit parameters.

    Attributes:
        action_type (str): Known ActionKind serialized value (lower_snake).
        parameters (dict[str, Any]): Typed payload for the action (e.g., {"agent_id": "..."}).
        score (float): Unnormalized score/logit used by the decision sampler.
        key (str): Compact, human-friendly label; program logic MUST NOT parse this.

    Raises:
        crv.core.errors.GrammarError: If action_type is not lower_snake or not a known ActionKind.

    Examples:
        >>> from crv.core.schema import ActionCandidate
        >>> cand = ActionCandidate(
        ...     action_type="acquire_token",
        ...     parameters={"agent_id": "i001", "token_id": "Alpha", "quantity": 1},
        ...     score=1.23,
        ...     key="acquire_token:token_id=Alpha",
        ... )
        >>> cand.action_type
        'acquire_token'
    """

    model_config = ConfigDict(extra="forbid")

    action_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    score: float
    key: str

    @field_validator("action_type", mode="before")
    @classmethod
    def _normalize_action_type(cls, v: Any) -> Any:
        """
        Normalize action_type via grammar.action_kind_from_value.

        Args:
            v (Any): Proposed action_type value.

        Returns:
            str: Canonical lower_snake action_type string (e.g., 'acquire_token').

        Raises:
            GrammarError: If not lower_snake or unknown ActionKind.
        """
        if v is None:
            return v
        try:
            return action_kind_from_value(str(v)).value
        except Exception as e:
            raise GrammarError(str(e)) from e


class DecisionHead(BaseModel):
    """
    Decision head output for an agent at a tick.

    Attributes:
        token_value_estimates (dict[str, float]): Estimated bounded valuation per token.
        action_candidates (list[ActionCandidate]): Candidate actions and scores.
        abstain (bool): Whether the agent abstains this tick.
        temperature (float): Sampling temperature for decision.

    Notes:
        token_value_estimates[token_id] ≈ V_agent(token) used to rank actions.

    Examples:
        >>> from crv.core.schema import DecisionHead, ActionCandidate
        >>> DecisionHead(action_candidates=[ActionCandidate(action_type="acquire_token", parameters={}, score=0.2, key="k")])
    """

    model_config = ConfigDict(extra="forbid")

    token_value_estimates: dict[str, float] = Field(default_factory=dict)
    action_candidates: list[ActionCandidate] = Field(default_factory=list)
    abstain: bool = False
    temperature: float = 0.0


# ============================================================================
# Context / Persona / Affect
# ============================================================================


class ScenarioContext(BaseModel):
    """
    Observer-centric scenario context snapshot used for valuation and decisions.

    Attributes:
        token_id (str | None): Optional token identifier.
        owner_status (str | None): Ownership status label.
        peer_alignment_label (str | None): Peer alignment label.
        group_label (str | None): Group label.
        visibility_scope (str | None): Normalized to {'public','group','room','dm'}.
        channel_name (str | None): Channel name (e.g., "group:G1").
        salient_agent_pairs (list[dict[str, Any]]): Salient agent pairs.
        exchange_snapshot (dict[str, Any]): Snapshot of exchange info (may include baseline_value).
        recent_affect_index (float | None): Recent affect index scalar.
        salient_other_agent_id (str | None): Salient other agent for this context.

    Raises:
        crv.core.errors.GrammarError: On invalid visibility_scope.

    Notes:
        visibility_scope is normalized via grammar.normalize_visibility.
        exchange_snapshot.baseline_value corresponds to B_token(t) when emitted by a venue.
    """

    model_config = ConfigDict(extra="forbid")

    token_id: str | None = None
    owner_status: str | None = None
    peer_alignment_label: str | None = None
    group_label: str | None = None
    visibility_scope: str | None = None
    channel_name: str | None = None
    salient_agent_pairs: list[dict[str, Any]] = Field(default_factory=list)
    exchange_snapshot: dict[str, Any] = Field(default_factory=dict)
    recent_affect_index: float | None = None
    salient_other_agent_id: str | None = None

    @field_validator("visibility_scope", mode="before")
    @classmethod
    def _normalize_visibility_scope(cls, v: Any) -> Any:
        """
        Normalize ScenarioContext.visibility_scope to {'public','group','room','dm'}.

        Args:
            v (Any): Proposed visibility scope.

        Returns:
            Any: Canonical lower_snake visibility string, or None.

        Raises:
            GrammarError: If not a recognized visibility class.
        """
        if v is None:
            return v
        try:
            return normalize_visibility(str(v))
        except Exception as e:
            raise GrammarError(str(e)) from e


class Persona(BaseModel):
    """
    Persona descriptor used to parameterize agent behavior.

    Attributes:
        persona_id (str): Stable identifier for the persona.
        label (str): Human-readable label.
        traits (dict[str, Any]): Free-form trait mapping used by downstream modules.
    """

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    label: str
    traits: dict[str, Any] = Field(default_factory=dict)


class AffectState(BaseModel):
    """
    Coarse affect state bounded to [0, 1].

    Attributes:
        valence (float): In [0, 1]. Defaults to 0.5.
        arousal (float): In [0, 1]. Defaults to 0.5.
        stress (float): In [0, 1]. Defaults to 0.0.
    """

    model_config = ConfigDict(extra="forbid")

    valence: float = Field(0.5, ge=0.0, le=1.0)
    arousal: float = Field(0.5, ge=0.0, le=1.0)
    stress: float = Field(0.0, ge=0.0, le=1.0)


# ============================================================================
# Rows
# ============================================================================


_ALLOWED_ENVELOPE_KINDS: set[str] = {"action", "observation"}
_ALLOWED_ENVELOPE_STATUS: set[str] = {"pending", "executed", "rejected"}
_ALLOWED_SIDES: set[str] = {"buy", "sell"}


class EventEnvelopeRow(BaseModel):
    """
    Envelope capturing scheduled actions or derived observations.

    Attributes:
        time_created (int): Time created.
        scheduled_step (int): Scheduled step.
        envelope_kind (str): One of {"action","observation"}.
        actor_agent_id (str | None): Actor agent id.
        observer_agent_id (str | None): Observer agent id.
        channel_name (str | None): Channel name.
        visibility_scope (str | None): One of {'public','group','room','dm'}.
        payload (JsonDict): Payload dictionary.
        origin (JsonDict): Origin metadata.
        status (str): One of {"pending","executed","rejected"}.

    Raises:
        crv.core.errors.GrammarError: For invalid envelope_kind/status/visibility.

    Notes:
        Logical staging structure; not a persisted table descriptor here.
        Downstream IO layers may map to event logs.
        visibility_scope is normalized via grammar.normalize_visibility (if present).
    """

    model_config = ConfigDict(extra="forbid")

    time_created: int
    scheduled_step: int
    envelope_kind: str
    actor_agent_id: str | None = None
    observer_agent_id: str | None = None
    channel_name: str | None = None
    visibility_scope: str | None = None
    payload: JsonDict = Field(default_factory=dict)
    origin: JsonDict = Field(default_factory=dict)
    status: str

    @field_validator("envelope_kind", mode="before")
    @classmethod
    def _normalize_envelope_kind(cls, v: Any) -> str:
        """
        Normalize EventEnvelopeRow.envelope_kind to {'action','observation'}.

        Args:
            v (Any): Proposed envelope kind.

        Returns:
            str: Canonical lower_snake string.

        Raises:
            GrammarError: If not one of the allowed kinds.
        """
        s = (v or "").lower()
        if s not in _ALLOWED_ENVELOPE_KINDS:
            raise GrammarError(f"envelope_kind must be one of {_ALLOWED_ENVELOPE_KINDS}, got {v!r}")
        return s

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Any) -> str:
        """
        Normalize EventEnvelopeRow.status to {'pending','executed','rejected'}.

        Args:
            v (Any): Proposed status.

        Returns:
            str: Canonical lower_snake status.

        Raises:
            GrammarError: If not one of the allowed statuses.
        """
        s = (v or "").lower()
        if s not in _ALLOWED_ENVELOPE_STATUS:
            raise GrammarError(f"status must be one of {_ALLOWED_ENVELOPE_STATUS}, got {v!r}")
        return s

    @field_validator("visibility_scope", mode="before")
    @classmethod
    def _normalize_visibility_event(cls, v: Any) -> Any:
        """
        Normalize EventEnvelopeRow.visibility_scope if provided.

        Args:
            v (Any): Proposed visibility scope.

        Returns:
            Any: Canonical lower_snake visibility string, or None.

        Raises:
            GrammarError: If not a recognized visibility class.
        """
        if v is None:
            return v
        try:
            return normalize_visibility(str(v))
        except Exception as e:
            raise GrammarError(str(e)) from e


class MessageRow(BaseModel):
    """
    Communication events emitted by agents.

    Attributes:
        tick (int): Tick at which the message is emitted.
        sender_agent_id (str): Sender agent id.
        channel_name (str): Channel name (e.g., "group:G1").
        visibility_scope (str): One of {'public','group','room','dm'}.
        audience (Any): Structured audience payload.
        speech_act (str): Speech act label.
        topic_label (str): Topic label.
        stance_label (str | None): Optional stance label.
        claims (Any): Structured claims payload.
        style (Any): Rhetorical/formatting style.

    Raises:
        crv.core.errors.GrammarError: On invalid visibility.

    Notes:
        Table mappings: messages (see tables.MESSAGES_DESC).
        visibility_scope is normalized via grammar.normalize_visibility.
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    sender_agent_id: str
    channel_name: str
    visibility_scope: str
    audience: Any
    speech_act: str
    topic_label: str
    stance_label: str | None = None
    claims: Any = Field(default_factory=dict)
    style: Any = Field(default_factory=dict)

    @field_validator("visibility_scope", mode="before")
    @classmethod
    def _normalize_visibility_msg(cls, v: Any) -> str:
        """
        Normalize MessageRow.visibility_scope.

        Args:
            v (Any): Proposed visibility scope.

        Returns:
            str: Canonical lower_snake visibility string.

        Raises:
            GrammarError: If not a recognized visibility class.
        """
        try:
            return normalize_visibility(str(v))
        except Exception as e:
            raise GrammarError(str(e)) from e


class ExchangeRow(BaseModel):
    """
    Generalized ownership/exchange events (beyond finance).

    Attributes:
        tick (int): Tick at which the event occurs.
        venue_id (str): Venue identifier.
        token_id (str): Token identifier.
        exchange_event_type (str): Exchange kind (lower_snake).
        side (str | None): One of {"buy","sell"}.
        quantity (float | None): Quantity transacted.
        price (float | None): Price.
        actor_agent_id (str | None): Actor agent id.
        counterparty_agent_id (str | None): Counterparty agent id.
        baseline_value (float | None): Baseline value emitted by venue, if any.
        additional_payload (dict[str, Any]): Venue-specific payload.

    Raises:
        crv.core.errors.GrammarError: On invalid exchange_event_type/side.

    Notes:
        Table mappings: exchange (see tables.EXCHANGE_DESC).
        exchange_event_type is normalized via grammar.exchange_kind_from_value.
        side is normalized case-insensitively to {"buy","sell"}.
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    venue_id: str
    token_id: str
    exchange_event_type: str
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    actor_agent_id: str | None = None
    counterparty_agent_id: str | None = None
    baseline_value: float | None = None
    additional_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("exchange_event_type", mode="before")
    @classmethod
    def _normalize_exchange_kind(cls, v: Any) -> Any:
        """
        Normalize ExchangeRow.exchange_event_type via grammar.exchange_kind_from_value.

        Args:
            v (Any): Proposed exchange event type.

        Returns:
            Any: Canonical lower_snake event type, or None.

        Raises:
            GrammarError: If not lower_snake or unknown exchange kind.
        """
        if v is None:
            return v
        try:
            return exchange_kind_from_value(str(v)).value
        except Exception as e:
            raise GrammarError(str(e)) from e

    @field_validator("side", mode="before")
    @classmethod
    def _normalize_side(cls, v: Any) -> Any:
        """
        Normalize ExchangeRow.side to {'buy','sell'} (case-insensitive).

        Args:
            v (Any): Proposed side value.

        Returns:
            Any: Canonical lower_snake side, or None.

        Raises:
            GrammarError: If not one of the allowed sides.
        """
        if v is None:
            return v
        s = str(v).lower()
        if s not in _ALLOWED_SIDES:
            raise GrammarError(f"side must be one of {_ALLOWED_SIDES}, got {v!r}")
        return s


class IdentityEdgeRow(BaseModel):
    """
    Unified identity/affect edge snapshots/deltas written to identity_edges.

    Attributes:
        tick (int): Tick at which the snapshot/delta is recorded.
        observer_agent_id (str): Observer agent identifier.
        edge_kind (str): RepresentationEdgeKind serialized value (lower_snake).
        subject_id (str | None): Subject agent identifier.
        object_id (str | None): Object/other agent identifier.
        related_agent_id (str | None): Related agent identifier (for agent-pair cases).
        token_id (str | None): Token identifier (when applicable).
        edge_weight (float): Measured edge weight.
        edge_sign (int | None): Optional sign encoding (0/1 or -1/1).

    Raises:
        crv.core.errors.GrammarError: On invalid edge_kind.
        crv.core.errors.SchemaError: When required field combinations are not met.

    Notes:
        - edge_kind is normalized via grammar.edge_kind_from_value.
        - Required field combinations are enforced via model_validator (see tests).

        Math mapping:
            - self_to_positive_valence      -> s^+_{agent}
            - self_to_negative_valence      -> s^-_{agent}
            - self_to_object                -> s_{agent,token}
            - self_to_agent                 -> a_{agent,other_agent}
            - agent_to_positive_valence     -> u^+_{agent,other_agent}
            - agent_to_negative_valence     -> u^-_{agent,other_agent}
            - agent_to_object               -> b_{agent,other_agent,token}
            - agent_to_agent                -> d_{agent,other_a,other_b}
            - agent_pair_to_object          -> q_{agent,other_a,other_b,token}
            - object_to_positive_valence    -> r^+_{agent,token}
            - object_to_negative_valence    -> r^-_{agent,token}
            - object_to_object              -> c_{agent,token_a,token_b}
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    observer_agent_id: str
    edge_kind: str

    # slots
    subject_id: str | None = None
    object_id: str | None = None
    related_agent_id: str | None = None
    token_id: str | None = None

    # measurements
    edge_weight: float
    edge_sign: int | None = None

    @field_validator("edge_kind", mode="before")
    @classmethod
    def _normalize_edge_kind_row(cls, v: Any) -> Any:
        """
        Normalize IdentityEdgeRow.edge_kind via grammar.edge_kind_from_value.

        Args:
            v (Any): Proposed edge_kind.

        Returns:
            Any: Canonical lower_snake edge_kind, or None.

        Raises:
            GrammarError: If not lower_snake or unknown edge kind.
        """
        if v is None:
            return v
        try:
            return edge_kind_from_value(str(v)).value
        except Exception as e:
            raise GrammarError(str(e)) from e

    @model_validator(mode="after")
    def _validate_combination(self) -> IdentityEdgeRow:
        """
        Enforce required field combinations per RepresentationEdgeKind.

        Returns:
            IdentityEdgeRow: Self, if validation succeeds.

        Raises:
            SchemaError: If required field combinations for the given edge_kind are not satisfied.
        """
        required_by_kind: dict[str, set[str]] = {
            "self_to_object": {"subject_id", "token_id"},
            "self_to_agent": {"subject_id", "object_id"},
            "agent_to_positive_valence": {"subject_id"},
            "agent_to_negative_valence": {"subject_id"},
            "agent_to_object": {"subject_id", "token_id"},
            "agent_to_agent": {"subject_id", "object_id"},
            "agent_pair_to_object": {"subject_id", "related_agent_id", "token_id"},
            "self_to_positive_valence": set(),
            "self_to_negative_valence": set(),
            "object_to_positive_valence": {"token_id"},
            "object_to_negative_valence": {"token_id"},
            "object_to_object": {"subject_id", "object_id"},
        }
        kind = self.edge_kind
        req = required_by_kind.get(kind)
        if req is None:
            raise SchemaError(f"unknown edge_kind combination policy: {kind!r}")

        missing = [name for name in req if not getattr(self, name)]
        if missing:
            raise SchemaError(
                f"edge_kind={kind!r} requires fields {sorted(req)}, missing: {missing}"
            )
        return self


class ScenarioRow(BaseModel):
    """
    Persisted observer-centric scenario context row used to reconstruct inputs.

    Attributes:
        tick (int): Tick of the scenario snapshot.
        observer_agent_id (str): Observer agent identifier.
        token_id (str | None): Optional token identifier.
        owner_status (str | None): Ownership status label.
        peer_alignment_label (str | None): Peer alignment label.
        group_label (str | None): Group label.
        visibility_scope (str | None): Normalized to {'public','group','room','dm'}.
        channel_name (str | None): Channel name.
        salient_agent_pairs (list[dict[str, Any]]): Salient agent pairs.
        exchange_snapshot (dict[str, Any]): Exchange snapshot (may include baseline_value).
        recent_affect_index (float | None): Recent affect index.
        salient_other_agent_id (str | None): Salient other agent id.
        context_hash (str): Canonical context hash.

    Raises:
        crv.core.errors.GrammarError: On invalid visibility_scope.

    Notes:
        Table mappings: scenarios_seen (see tables.SCENARIOS_SEEN_DESC).
        visibility_scope is normalized via grammar.normalize_visibility.
        exchange_snapshot.baseline_value corresponds to B_token(t).
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    observer_agent_id: str
    token_id: str | None = None
    owner_status: str | None = None
    peer_alignment_label: str | None = None
    group_label: str | None = None
    visibility_scope: str | None = None
    channel_name: str | None = None
    salient_agent_pairs: list[dict[str, Any]] = Field(default_factory=list)
    exchange_snapshot: dict[str, Any] = Field(default_factory=dict)
    recent_affect_index: float | None = None
    salient_other_agent_id: str | None = None
    context_hash: str

    @field_validator("visibility_scope", mode="before")
    @classmethod
    def _normalize_visibility_scen(cls, v: Any) -> Any:
        """
        Normalize ScenarioRow.visibility_scope via grammar.normalize_visibility.

        Args:
            v (Any): Proposed visibility scope.

        Returns:
            Any: Canonical lower_snake visibility string, or None.

        Raises:
            GrammarError: If not a recognized visibility class.
        """
        if v is None:
            return v
        try:
            return normalize_visibility(str(v))
        except Exception as e:
            raise GrammarError(str(e)) from e


class DecisionRow(BaseModel):
    """
    Agent decision outputs per tick.

    Attributes:
        tick (int): Tick of the decision.
        agent_id (str): Agent identifier.
        chosen_action (dict[str, Any]): Chosen action payload.
        action_candidates (list[dict[str, Any]]): Candidate actions payloads.
        token_value_estimates (dict[str, float]): Estimated values per token.

    Notes:
        Table mappings: decisions (see tables.DECISIONS_DESC).
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    agent_id: str
    chosen_action: dict[str, Any]
    action_candidates: list[dict[str, Any]]
    token_value_estimates: dict[str, float]


class OracleCallRow(BaseModel):
    """
    LLM/tooling calls with persona/context and cache metadata.

    Attributes:
        tick (int): Tick of the call.
        agent_id (str): Agent identifier.
        engine (str): Inference engine label.
        signature_id (str): Signature identifier.
        persona_id (str): Persona identifier.
        persona_hash (str): Canonical persona hash.
        representation_hash (str): Canonical representation hash.
        context_hash (str): Canonical context hash.
        value_json (str): Serialized value JSON.
        latency_ms (int): Latency in milliseconds.
        cache_hit (bool): Whether cache was hit.
        n_tool_calls (int): Number of tool calls.
        tool_seq (dict[str, Any]): Tool call sequence metadata.

    Notes:
        Table mappings: oracle_calls (see tables.ORACLE_CALLS_DESC).
        cache_hit is persisted as i64 (0/1) in descriptors to adhere to allowed dtypes.
    """

    model_config = ConfigDict(extra="forbid")

    tick: int
    agent_id: str
    engine: str
    signature_id: str
    persona_id: str
    persona_hash: str
    representation_hash: str
    context_hash: str
    value_json: str
    latency_ms: int
    cache_hit: bool
    n_tool_calls: int
    tool_seq: dict[str, Any] = Field(default_factory=dict)
