from src.crv.core.grammar import TableName, is_lower_snake
from src.crv.core.tables import get_table, list_tables
from src.crv.core.versioning import SCHEMA_V


def test_descriptors_contract() -> None:
    for desc in list_tables():
        # column names lower_snake
        for col in desc.columns.keys():
            assert is_lower_snake(col), f"column {col!r} not lower_snake for {desc.name.value}"
        # required subset of columns
        assert set(desc.required).issubset(desc.columns.keys()), (
            f"required not subset of columns for {desc.name.value}"
        )
        # required/nullable disjoint
        assert set(desc.required).isdisjoint(desc.nullable), (
            f"required/nullable not disjoint for {desc.name.value}"
        )
        # required ∪ nullable ⊆ columns
        assert set(desc.required).union(desc.nullable).issubset(desc.columns.keys()), (
            f"required∪nullable not subset of columns for {desc.name.value}"
        )
        # partitioning exactly ["bucket"]
        assert desc.partitioning == ["bucket"], f"partitioning mismatch for {desc.name.value}"
        # `bucket` present and required
        assert "bucket" in desc.columns, f"bucket missing in columns for {desc.name.value}"
        assert "bucket" in desc.required, f"bucket not required for {desc.name.value}"
        # version pins to SCHEMA_V
        assert desc.version == SCHEMA_V, f"version mismatch for {desc.name.value}"


def test_get_table_roundtrip() -> None:
    for name in TableName:
        desc = get_table(name)
        assert desc.name == name
