"""
Schema validation utilities for crv.io.

Purpose
- Validate Polars DataFrames against canonical table descriptors from crv.core.tables.
- Apply pragmatic checks with safe casting for scalar dtypes.

Source of truth (core)
- crv.core.tables.TableDescriptor describes columns/dtypes/required/nullable/partitioning.
- crv.core.grammar.TableName enumerates canonical table names.
- crv.core.schema defines row-level combination rules (not enforced here).
- crv.core.errors provides domain exceptions (SchemaError/GrammarError). The IO layer raises
  IoSchemaError for validation failures at the IO boundary.

Checks performed (Phase 1)
- Required columns present.
- When strict=True: no columns outside (required ∪ nullable).
- Dtype compatibility:
  - Scalar types ("i64","f64","str") are safely cast when possible.
  - "struct" accepts pl.Struct or pl.Object (no deep validation).
  - "list[struct]" accepts pl.List (inner type not enforced yet).

Notes
- File protocol baseline only; this module depends on polars and crv.core descriptors.
"""

from __future__ import annotations

from collections.abc import Iterable

import polars as pl

from crv.core.grammar import TableName
from crv.core.tables import TableDescriptor, get_table

from .errors import IoSchemaError

# Note: Polars exposes dtype singletons/classes (e.g., pl.Int64). To keep the type checker happy
# across versions, keep this mapping loosely typed.
_DTYPE_MAP: dict[str, object] = {
    "i64": pl.Int64,
    "f64": pl.Float64,
    "str": pl.Utf8,
    # "struct" and "list[struct]" handled specially
}


def _is_struct_like(dtype: pl.DataType) -> bool:
    # Accept both Struct and Object for early-phase flexibility.
    return isinstance(dtype, pl.Struct) or dtype == pl.Object


def _is_list_like(dtype: pl.DataType) -> bool:
    return isinstance(dtype, pl.List)


def _compatible_dtype(expected: str, actual: pl.DataType) -> bool:
    if expected in _DTYPE_MAP:
        return actual == _DTYPE_MAP[expected]
    if expected == "struct":
        return _is_struct_like(actual)
    if expected == "list[struct]":
        return _is_list_like(actual)
    # Unknown descriptor dtype
    return False


def _safe_cast(df: pl.DataFrame, col: str, target: object) -> pl.DataFrame:
    try:
        # Polars dtypes are singleton-like objects (e.g., pl.Int64); type checker may not resolve.
        return df.with_columns(pl.col(col).cast(target, strict=False))  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - defensive
        raise IoSchemaError(f"failed to cast column {col!r} to {target}: {exc}") from exc


def _ensure_columns_present(df: pl.DataFrame, needed: Iterable[str]) -> None:
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise IoSchemaError(f"missing required columns: {missing!r}")


def _ensure_no_extra_columns(df: pl.DataFrame, allowed: set[str]) -> None:
    extras = [c for c in df.columns if c not in allowed]
    if extras:
        raise IoSchemaError(f"unexpected columns present: {extras!r} (allowed={sorted(allowed)!r})")


def validate_frame_against_descriptor(
    df: pl.DataFrame,
    desc: TableDescriptor,
    *,
    strict: bool = True,
) -> pl.DataFrame:
    """
    Validate a Polars DataFrame against a TableDescriptor.

    Args:
        df (pl.DataFrame): Frame to validate.
        desc (TableDescriptor): Canonical descriptor from crv.core.tables.
        strict (bool): Enforce exact column set (no extras) when True.

    Returns:
        pl.DataFrame: Possibly with safe casts applied for scalar types.

    Raises:
        IoSchemaError: If required columns are missing, extras are present under strict mode, or dtypes are incompatible and cannot be safely cast.

    Notes:
        - Scalar columns ("i64","f64","str"): attempt non-strict casts.
        - Struct-like columns accept pl.Struct or pl.Object.
        - List[struct] accepts any pl.List inner type in Phase 1.
    """
    # Ensure presence and no extras (strict)
    required = set(desc.required)
    nullable = set(desc.nullable)
    all_known = required | nullable
    _ensure_columns_present(df, required)
    if strict:
        _ensure_no_extra_columns(df, all_known)

    # Type checks + casting for scalar types
    for col, dtype_name in desc.columns.items():
        if col not in df.columns:
            # Required columns must be present; missing optional/nullable columns are allowed.
            if col in required:
                raise IoSchemaError(f"column {col!r} is required by schema")
            continue
        actual = df.schema[col]
        if dtype_name in _DTYPE_MAP:
            expected = _DTYPE_MAP[dtype_name]
            if actual != expected:
                # Attempt a safe cast to expected scalar dtype
                df = _safe_cast(df, col, expected)
        elif dtype_name == "struct":
            if not _compatible_dtype(dtype_name, actual):
                raise IoSchemaError(f"column {col!r} expected struct-like dtype; got {actual}")
        elif dtype_name == "list[struct]":
            if not _compatible_dtype(dtype_name, actual):
                raise IoSchemaError(f"column {col!r} expected list-like dtype; got {actual}")
        else:  # pragma: no cover - defensive
            raise IoSchemaError(f"unknown descriptor dtype {dtype_name!r} for column {col!r}")

    return df


def validate_frame_for_table(
    df: pl.DataFrame,
    table: TableName | str,
    *,
    strict: bool = True,
) -> pl.DataFrame:
    """
    Validate a DataFrame against the descriptor for a given table.

    Args:
        df (pl.DataFrame): DataFrame to validate.
        table (TableName | str): Canonical table name (enum or lower_snake string).
        strict (bool): Enforce exact column set when True.

    Returns:
        pl.DataFrame: Possibly casted frame.

    Raises:
        crv.io.errors.IoSchemaError: On validation failure.

    Notes:
        - Resolves the descriptor from crv.core.tables via the TableName enum.
        - Row-level semantic checks (e.g., combination rules) live in crv.core.schema.
    """
    tname = table.value if isinstance(table, TableName) else str(table)
    desc = get_table(TableName(tname))
    return validate_frame_against_descriptor(df, desc, strict=strict)
