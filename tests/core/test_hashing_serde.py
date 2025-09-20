from crv.core.hashing import hash_row, json_dumps_canonical
from crv.core.serde import json_dumps_canonical as serde_dumps
from crv.core.serde import json_loads


def test_json_dumps_canonical_sorted_and_ascii_policy() -> None:
    obj1 = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}, "emoji": "🙂"}
    obj2 = {"nested": {"x": 1, "y": 2}, "a": 1, "emoji": "🙂", "b": 2}
    s1 = json_dumps_canonical(obj1)
    s2 = json_dumps_canonical(obj2)
    assert s1 == s2  # order-insensitive; keys sorted canonically
    # ensure_ascii=False keeps unicode as-is (no escape sequences)
    assert "🙂" in s1


def test_hash_row_order_invariant() -> None:
    row_a = {"x": 1, "y": 2, "z": {"b": 2, "a": 1}}
    row_b = {"z": {"a": 1, "b": 2}, "y": 2, "x": 1}
    h_a = hash_row(row_a)
    h_b = hash_row(row_b)
    assert h_a == h_b


def test_serde_roundtrip_and_reexport() -> None:
    obj = {"k": [1, 2, 3], "m": {"n": 4}}
    s = serde_dumps(obj)
    back = json_loads(s)
    assert back == obj
