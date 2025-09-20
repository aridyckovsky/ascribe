"""Schema version metadata for CRV JSON schemas and Polars tables.

The core layer exposes a single canonical schema version (`SCHEMA_V`) that all
downstream components (lab exporters, viz loaders, documentation) reference to
ensure CRV artifacts remain compatible with the published data contracts.
"""

from dataclasses import dataclass
from datetime import date

SCHEMA_MAJOR_VERSION = 1
SCHEMA_MINOR_VERSION = 0


@dataclass(frozen=True)
class SchemaVersion:
    """Immutable semantic version with ISO release date for CRV artifacts.

    Attributes
    ----------
    major:
        Non-negative major schema component signalling breaking changes.
    minor:
        Non-negative minor component for additive, backward-compatible changes.
    date:
        Release timestamp in ISO ``YYYY-MM-DD`` form retained for JSON/metadata
        payloads.

    Raises
    ------
    ValueError
        If any component is negative or the date is not ISO compliant.
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
    """Return ``True`` when ``ver`` matches the supported schema contract.

    Parameters
    ----------
    ver:
        Version descriptor to validate against the canonical schema metadata.

    Returns
    -------
    bool
        ``True`` if ``ver`` shares both the major and minor numbers with
        ``SCHEMA_V``; ``False`` otherwise.
    """

    return ver.major == SCHEMA_COMPAT_MAJOR and ver.minor == SCHEMA_COMPAT_MINOR


def is_successor_of(candidate: SchemaVersion, current: SchemaVersion) -> bool:
    """Return ``True`` when ``candidate`` is the immediate successor of ``current``.

    CRV schema updates follow semantic-version semantics: minor bumps increase
    the minor component while keeping the major fixed, and major bumps increase
    the major component by exactly one while resetting the minor to zero.
    Larger jumps (skipping minor numbers or jumping more than one major
    version) are treated as non-sequential.

    Parameters
    ----------
    candidate:
        Proposed schema revision.
    current:
        Baseline schema version currently supported.

    Returns
    -------
    bool
        ``True`` if ``candidate`` immediately follows ``current``; ``False``
        otherwise.
    """

    if candidate.major == current.major:
        return candidate.minor == current.minor + 1
    if candidate.major == current.major + 1 and candidate.minor == 0:
        return True
    return False
