"""Tests for `crv.core.versioning` schema version helpers."""

import pytest

from src.crv.core.versioning import (
    SCHEMA_COMPAT_MAJOR,
    SCHEMA_COMPAT_MINOR,
    SchemaVersion,
    is_compatible,
    is_successor_of,
)


def test_schema_version_accepts_iso_date() -> None:
    version = SchemaVersion(
        major=SCHEMA_COMPAT_MAJOR,
        minor=SCHEMA_COMPAT_MINOR,
        date="2025-09-20",
    )

    assert version.date == "2025-09-20"
    assert version.major == SCHEMA_COMPAT_MAJOR
    assert version.minor == SCHEMA_COMPAT_MINOR


@pytest.mark.parametrize("bad_date", ["2025/09/20", "2025-9-2", "20-09-2025"])
def test_schema_version_rejects_non_iso_date(bad_date: str) -> None:
    with pytest.raises(ValueError, match="SchemaVersion date must be ISO"):
        SchemaVersion(major=SCHEMA_COMPAT_MAJOR, minor=0, date=bad_date)


@pytest.mark.parametrize("field,value", [("major", -1), ("minor", -1)])
def test_schema_version_rejects_negative_components(field: str, value: int) -> None:
    kwargs = {"major": SCHEMA_COMPAT_MAJOR, "minor": SCHEMA_COMPAT_MINOR, "date": "2025-09-20"}
    kwargs[field] = value

    with pytest.raises(ValueError, match=f"SchemaVersion {field} must be non-negative"):
        SchemaVersion(**kwargs)


def test_is_compatible_checks_major_component() -> None:
    compatible = SchemaVersion(
        major=SCHEMA_COMPAT_MAJOR,
        minor=SCHEMA_COMPAT_MINOR,
        date="2025-09-20",
    )
    wrong_major = SchemaVersion(
        major=SCHEMA_COMPAT_MAJOR + 1,
        minor=SCHEMA_COMPAT_MINOR,
        date="2025-09-20",
    )
    wrong_minor = SchemaVersion(
        major=SCHEMA_COMPAT_MAJOR,
        minor=SCHEMA_COMPAT_MINOR + 1,
        date="2025-09-20",
    )

    assert is_compatible(compatible) is True
    assert is_compatible(wrong_major) is False
    assert is_compatible(wrong_minor) is False


def test_is_successor_of_minor_bump() -> None:
    current = SchemaVersion(major=1, minor=0, date="2025-09-20")
    candidate = SchemaVersion(major=1, minor=1, date="2025-09-21")

    assert is_successor_of(candidate, current) is True


def test_is_successor_of_major_bump() -> None:
    current = SchemaVersion(major=1, minor=3, date="2025-09-20")
    candidate = SchemaVersion(major=2, minor=0, date="2025-09-21")

    assert is_successor_of(candidate, current) is True


@pytest.mark.parametrize(
    "candidate,current",
    [
        (SchemaVersion(1, 3, "2025-09-22"), SchemaVersion(1, 1, "2025-09-20")),
        (SchemaVersion(2, 1, "2025-09-22"), SchemaVersion(1, 4, "2025-09-20")),
        (SchemaVersion(3, 0, "2025-09-22"), SchemaVersion(1, 4, "2025-09-20")),
    ],
)
def test_is_successor_of_rejects_skipped_versions(
    candidate: SchemaVersion, current: SchemaVersion
) -> None:
    assert is_successor_of(candidate, current) is False
