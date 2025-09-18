from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "Acquire",
    "Relinquish",
    "CentralExchange",
    "PeerExchange",
    "Expose",
    "Endorse",
    "Relate",
    "Cooccur",
    "Chat",
    "Event",
]

# Typed context-event grammar ---------------------------------


@dataclass(frozen=True)
class Acquire:
    """Context event recording when an agent obtains a token in the CRV loop.

    The acquisition strengthens the self→object link (:math:`s_{i,o}`) and sets the
    endowment baseline used during valuation readout. Central planners can mark
    the event as a free choice or an assigned transfer to distinguish agency in later
    analyses.

    Args:
        i: Index of the receiving agent within the model roster.
        o: Index of the token now owned by the agent.
        mode: Exchange mode flag, either ``"choice"`` for voluntary uptake or
            ``"assigned"`` for administrative allocation.

    Examples:
        >>> Acquire(i=2, o=5)
        Acquire(i=2, o=5, mode='choice')
        >>> Acquire(i=7, o=3, mode="assigned")
        Acquire(i=7, o=3, mode='assigned')
    """

    i: int
    o: int
    mode: Literal["choice", "assigned"] = "choice"


@dataclass(frozen=True)
class Relinquish:
    """Context event signifying that an agent releases a token.

    Relinquishment attenuates :math:`s_{i,o}` in the agent's representation and
    prompts downstream affective decay for the associated object.

    Args:
        i: Index of the agent letting go of the token.
        o: Index of the token being removed from the agent's endowment.

    Examples:
        >>> Relinquish(i=4, o=1)
        Relinquish(i=4, o=1)
    """

    i: int
    o: int


@dataclass(frozen=True)
class CentralExchange:
    """Opaque, venue-mediated trade used for centralized market events.

    The black-box exchange updates holdings without revealing counterparties,
    which is useful when modeling institutional clearing houses or aggregated pool
    swaps. Quantities use integer counts; negative sizes should be normalized before
    instantiating the event for speed.

    Args:
        i: Index of the submitting agent.
        delivered: Ordered tuples of ``(token, quantity)`` describing what the agent
            sends to the venue. Quantities must be non-negative integers.
        received: Ordered tuples of ``(token, quantity)`` describing what the agent
            receives from the venue.

    Examples:
        >>> CentralExchange(i=1, delivered=((2, 3),), received=((5, 1), (8, 2)))
        CentralExchange(i=1, delivered=((2, 3),), received=((5, 1), (8, 2)))
    """

    i: int
    delivered: tuple[tuple[int, int], ...]
    received: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class PeerExchange:
    """Bilateral swap where two agents exchange individual tokens.

    The event simultaneously reduces :math:`s_{i,o}` and :math:`s_{j,p}` while
    increasing :math:`s_{i,p}` and :math:`s_{j,o}`, supporting symmetric valuation
    updates with minimal bookkeeping.

    Args:
        i: Index of the first agent.
        j: Index of the second agent.
        o: Token index moving from agent ``i`` to agent ``j``.
        p: Token index moving from agent ``j`` to agent ``i``.

    Examples:
        >>> PeerExchange(i=0, j=6, o=4, p=9)
        PeerExchange(i=0, j=6, o=4, p=9)
    """

    i: int
    j: int
    o: int
    p: int


@dataclass(frozen=True)
class Expose:
    """Exposure event delivering affective evidence about a token to an agent.

    Exposure modifies the affect accumulator :math:`r_{i,o}^{+/-}` depending on
    the valence, which in turn shapes valuation bursts and triad coherence.

    Args:
        i: Index of the agent perceiving the cue.
        o: Index of the token referenced by the cue.
        val: Valence indicator, with ``1`` for positive cues and ``-1`` for negative
            cues.

    Examples:
        >>> Expose(i=5, o=12, val=1)
        Expose(i=5, o=12, val=1)
    """

    i: int
    o: int
    val: Literal[1, -1]


@dataclass(frozen=True)
class Endorse:
    """Social stance communication shaping perceived norms and ownership.

    Endorsements gate the triadic link :math:`b_{i,j,o}` and adjust the relational
    affect between agents. Positive values reinforce alignment; negative values feed
    conflict dynamics.

    Args:
        j: Index of the messenger agent conveying the stance.
        i: Index of the receiving agent.
        o: Index of the token under discussion.
        val: Valence indicator, with ``1`` for an endorsement and ``-1`` for a
            rejection.

    Examples:
        >>> Endorse(j=3, i=2, o=10, val=-1)
        Endorse(j=3, i=2, o=10, val=-1)
    """

    j: int
    i: int
    o: int
    val: Literal[1, -1]


@dataclass(frozen=True)
class Relate:
    """Dyadic relationship event capturing alliance or conflict alignment.

    Relationship events update the self→other link :math:`a_{i,j}` and its
    counterpart, mediating how social structure shapes valuation spillovers.

    Args:
        i: Index of the focal agent.
        j: Index of the partner agent.
        val: Relationship valence, with ``1`` indicating alliance and ``-1``
            indicating opposition.

    Examples:
        >>> Relate(i=1, j=9, val=1)
        Relate(i=1, j=9, val=1)
    """

    i: int
    j: int
    val: Literal[1, -1]


@dataclass(frozen=True)
class Cooccur:
    """Semantic association event linking two tokens in an agent's frame.

    Co-occurrence strengthens object–object channels :math:`c_{i,o,o'}` used during
    balanced-identity updates to propagate contextual meaning.

    Args:
        o: Index of the first token in the association.
        op: Index of the second token in the association.

    Examples:
        >>> Cooccur(o=2, op=7)
        Cooccur(o=2, op=7)
    """

    o: int
    op: int


# NOTE: Chat events may contain arbitrary text and are thus a potential vector for
# injection attacks if used in untrusted contexts. Exercise caution when processing
# or displaying chat content.
# TODO: Consider adding a 'channel' field to denote public vs. private messages.
@dataclass(frozen=True)
class Chat:
    """Free-form conversational exchange between agents for social reasoning.

    Chat events complement endorsement and exposure signals by transporting raw
    dialogue that downstream components can parse for stance, affect, or intent.
    Recipients may be empty to denote a broadcast to the wider context. Messages are
    stored verbatim to allow deferred natural-language processing.

    Args:
        sender: Index of the agent emitting the message.
        recipients: Ordered indices of target agents. Use an empty tuple for
            broadcast-style messages.
        content: Raw message text as produced during simulation.

    Examples:
        >>> Chat(sender=0, recipients=(2,), content="Let's coordinate on token 7.")
        Chat(sender=0, recipients=(2,), content='Let's coordinate on token 7.')
    """

    sender: int
    recipients: tuple[int, ...]
    content: str


Event = (
    Acquire
    | Relinquish
    | CentralExchange
    | PeerExchange
    | Expose
    | Endorse
    | Relate
    | Cooccur
    | Chat
)
