"""
Lightweight typing aliases used across core schemas and tables.

Provides minimal NewTypes and aliases to improve readability and static checks.
This module contains no runtime logic and is zero-IO.

Notes:
    - Intended for use in annotations across schemas and downstream modules.
    - Keep the surface small and stable to avoid churn in dependents.

Examples:
    Use aliases in annotations.

    >>> from crv.core.typing import Tick, GroupId, RoomId, JsonDict
    >>> def advance(t: Tick) -> Tick:
    ...     return Tick(int(t) + 1)
    >>> advance(Tick(10))
    10
    >>> def describe_room(room: RoomId) -> str:
    ...     return f"room:{room}"
    >>> describe_room(RoomId("market"))
    'room:market'
    >>> def payload() -> JsonDict:
    ...     return {"a": 1, "b": 2}
"""

from __future__ import annotations

from typing import Any, NewType

__all__ = [
    "Tick",
    "GroupId",
    "RoomId",
    "JsonDict",
]

# NewType wrappers for semantic clarity in rows/schemas.
Tick = NewType("Tick", int)
# TODO: Consider moving these to ids.py?
# TODO: Alternatively, combine ids into typing if both are relatively small?
GroupId = NewType("GroupId", str)
RoomId = NewType("RoomId", str)

# Convenient JSON-like mapping alias. Kept intentionally broad for serde boundaries.
JsonDict = dict[str, Any]
