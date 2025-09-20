"""
Canonical JSON serialization and hashing helpers for core schemas.

Provides a single canonical JSON policy and SHA-256 helpers to ensure stable,
order-insensitive serialization and hashing across runs and consumers. This
module is zero-IO and uses only the Python standard library.

Notes:
    - Canonical JSON:
        - sort_keys=True
        - separators=(",", ":")
        - ensure_ascii=False
    - Hashing is performed over the UTF-8 encoded canonical JSON string.
    - Used by core/tests/downstream packages to keep identifiers stable.

References:
    - specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

__all__ = [
    "json_dumps_canonical",
    "hash_row",
    "hash_context",
    "hash_state",
]


def json_dumps_canonical(obj: Any) -> str:
    """
    Serialize an object to a canonical JSON string.

    Args:
        obj (Any): JSON-serializable object.

    Returns:
        str: Canonical JSON string with sort_keys=True, compact separators,
        and ensure_ascii=False.

    Notes:
        This function assumes the input is JSON-serializable and does not perform
        coercion of unsupported types.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hexdigest(s: str) -> str:
    """Compute SHA-256 hex digest of a UTF-8 string."""
    h = hashlib.sha256()
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def hash_row(row: Mapping[str, Any]) -> str:
    """
    Compute a stable hash for a row-like mapping by hashing its canonical JSON.

    Args:
        row (Mapping[str, Any]): Row mapping (e.g., dict) to hash.

    Returns:
        str: SHA-256 hex digest over the canonical JSON serialization.

    Notes:
        Re-ordering keys in the mapping does not change the result.
    """
    return _sha256_hexdigest(json_dumps_canonical(dict(row)))


def hash_context(ctx_json: Mapping[str, Any]) -> str:
    """
    Hash a context-like mapping using canonical JSON and SHA-256 policy.

    Args:
        ctx_json (Mapping[str, Any]): Context mapping to hash.

    Returns:
        str: SHA-256 hex digest over the canonical JSON serialization.
    """
    return _sha256_hexdigest(json_dumps_canonical(dict(ctx_json)))


def hash_state(agent_state: Mapping[str, Any]) -> str:
    """
    Hash an agent state mapping using canonical JSON and SHA-256 policy.

    Args:
        agent_state (Mapping[str, Any]): Agent state mapping to hash.

    Returns:
        str: SHA-256 hex digest over the canonical JSON serialization.

    Examples:
        >>> from crv.core.hashing import hash_state
        >>> hash_state({"a": 1}) == hash_state({"a": 1})
        True
    """
    return _sha256_hexdigest(json_dumps_canonical(dict(agent_state)))
