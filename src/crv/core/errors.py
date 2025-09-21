"""
Core exception types raised by grammar validation, schema checks, and versioning.

Provides typed exceptions for core-domain failures:
- GrammarError for grammar/naming/normalization violations.
- SchemaError for schema-level constraints and cross-field combination rules.
- VersionMismatch for schema version incompatibilities against SCHEMA_V.

Notes:
    - This module uses only the Python standard library and has no side effects.
    - Validators in crv.core.schema raise:
        - GrammarError for naming/normalization failures.
        - SchemaError for combination/range violations.
    - Version guards raise VersionMismatch when artifacts do not match SCHEMA_V.

Examples:
    Catch a normalization failure.

    >>> from crv.core.errors import GrammarError
    >>> def normalize_demo(s: str) -> str:
    ...     if any(c.isupper() for c in s):
    ...         raise GrammarError("value must be lower_snake")
    ...     return s
    >>> try:
    ...     normalize_demo("Not_Lower_Snake")
    ... except GrammarError as e:
    ...     msg = str(e)
    >>> "lower_snake" in msg
    True
"""

from __future__ import annotations

__all__ = [
    "SchemaError",
    "VersionMismatch",
    "GrammarError",
]


class SchemaError(ValueError):
    """Schema-level validation failure (shape, constraints, cross-field rules)."""


class VersionMismatch(RuntimeError):
    """Incompatible or unexpected schema version encountered."""


class GrammarError(ValueError):
    """Grammar/naming normalization failure (e.g., not lower_snake or invalid enum value)."""
