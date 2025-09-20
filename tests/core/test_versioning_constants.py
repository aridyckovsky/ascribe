"""Guards against drift between SCHEMA_V and module-level constants."""

from crv.core.versioning import SCHEMA_MAJOR_VERSION, SCHEMA_MINOR_VERSION, SCHEMA_V


def test_version_constants_match_schema_v() -> None:
    assert SCHEMA_MAJOR_VERSION == SCHEMA_V.major
    assert SCHEMA_MINOR_VERSION == SCHEMA_V.minor
