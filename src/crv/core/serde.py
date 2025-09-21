"""
Lightweight JSON serialization/deserialization utilities.

Provides `json_loads` as a thin wrapper around the stdlib `json` module and
re-exports `json_dumps_canonical` from `crv.core.hashing` to ensure a single
canonical JSON policy across the codebase. This module is zero-IO.

Notes:
    - Use `json_dumps_canonical` for deterministic JSON strings prior to hashing,
      caching, or persistence.
    - No side effects; stdlib-only.

References:
    - specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
"""

from __future__ import annotations

import json
from typing import Any

# Re-export canonical dumps to keep a single canonicalization policy.
from .hashing import json_dumps_canonical  # noqa: F401

__all__ = [
    "json_loads",
    "json_dumps_canonical",
]


def json_loads(s: str) -> Any:
    """
    Deserialize a JSON string to Python objects using the stdlib json module.

    Args:
        s (str): JSON string to parse.

    Returns:
        Any: Decoded Python object (dict, list, str, int, float, bool, or None).

    Notes:
        - No datetime parsing or custom hooks here; the core remains pure.
        - For canonical serialization (for hashing), use `json_dumps_canonical`.
    """
    return json.loads(s)
