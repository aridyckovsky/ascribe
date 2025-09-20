"""
Schema version metadata and helpers for CRV JSON schemas and table descriptors.

Exposes the canonical schema version (SCHEMA_V) used across artifacts and
provides compatibility and successor checks. This module is zero-IO.

Notes:
    - Downstream components embed SCHEMA_V to tag produced artifacts.
    - Tests assert constants match SCHEMA_V and validate bump sequences.
    - Loaders/writers may use is_compatible to enforce contract alignment.

References:
    - specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
    - ADR: src/crv/core/.specs/adr-2025-09-20-core-schema-0.1-and-graphedit-normalization.md
"""

from dataclasses import dataclass
from datetime import date

SCHEMA_MAJOR_VERSION = 0
SCHEMA_MINOR_VERSION = 1


@dataclass(frozen=True)
class SchemaVersion:
    """
    Immutable semantic version with ISO release date for CRV artifacts.

    Attributes:
        major (int): Non-negative major component signalling breaking changes.
        minor (int): Non-negative minor component for additive, non-breaking changes.
        date (str): ISO YYYY-MM-DD release timestamp retained for JSON/metadata payloads.

    Raises:
        ValueError: If any component is negative or the date is not ISO compliant.
    """

    major: int
    minor: int
    date: str  # ISO YYYY-MM-DD

    def __post_init__(self) -> None:
        if self.major < 0:
            raise ValueError(f"SchemaVersion major must be non-negative, got {self.major}")
        if self.minor < 0:
            raise ValueError(f"SchemaVersion minor must be non-negative, got {self.minor}")
        try:
            date.fromisoformat(self.date)
        except ValueError as exc:
            raise ValueError(
                f"SchemaVersion date must be ISO YYYY-MM-DD, got {self.date!r}"
            ) from exc


SCHEMA_V = SchemaVersion(0, 1, "2025-09-20")
SCHEMA_COMPAT_MAJOR = SCHEMA_V.major
SCHEMA_COMPAT_MINOR = SCHEMA_V.minor


def is_compatible(ver: SchemaVersion) -> bool:
    """
    Check whether a version matches the supported schema contract.

    Args:
        ver (SchemaVersion): Version descriptor to validate against the canonical schema metadata.

    Returns:
        bool: True if ver shares both the major and minor numbers with SCHEMA_V; False otherwise.

    Examples:
        >>> from crv.core.versioning import SchemaVersion, SCHEMA_V, is_compatible
        >>> is_compatible(SCHEMA_V)
        True
    """
    return ver.major == SCHEMA_COMPAT_MAJOR and ver.minor == SCHEMA_COMPAT_MINOR


def is_successor_of(candidate: SchemaVersion, current: SchemaVersion) -> bool:
    """
    Determine whether a version is the immediate successor of another.

    CRV schema updates follow semantic versioning semantics:
      - Minor bumps increase the minor component while keeping the major fixed.
      - Major bumps increase the major component by exactly one and reset minor to zero.
      - Larger jumps (skipping minor numbers or jumping more than one major version) are non-sequential.

    Args:
        candidate (SchemaVersion): Proposed schema revision.
        current (SchemaVersion): Baseline schema version currently supported.

    Returns:
        bool: True if candidate immediately follows current; False otherwise.

    Examples:
        >>> from crv.core.versioning import SchemaVersion, SCHEMA_V, is_successor_of
        >>> is_successor_of(SchemaVersion(SCHEMA_V.major, SCHEMA_V.minor + 1, SCHEMA_V.date), SCHEMA_V)
        True
        >>> is_successor_of(SchemaVersion(SCHEMA_V.major + 1, 0, SCHEMA_V.date), SCHEMA_V)
        True
        >>> is_successor_of(SchemaVersion(SCHEMA_V.major, SCHEMA_V.minor + 2, SCHEMA_V.date), SCHEMA_V)
        False
    """
    if candidate.major == current.major:
        return candidate.minor == current.minor + 1
    if candidate.major == current.major + 1 and candidate.minor == 0:
        return True
    return False
