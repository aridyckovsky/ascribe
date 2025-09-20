"""
Frozen table descriptors for CRV canonical datasets (Parquet/Arrow-like).

Notes:
    - Descriptors declare column names/dtypes, partitioning, required/nullable
      columns, and the pinned schema version.
    - Column names are lower_snake.
    - Partitioning is always ["bucket"]; IO layers compute bucket as
      tick // TICK_BUCKET_SIZE.
    - Core is zero-IO (stdlib only); downstream IO (crv.io) materializes schemas.

References:
    - specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
"""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import TableName
from .versioning import SCHEMA_V, SchemaVersion

__all__ = [
    "TableDescriptor",
    "EXCHANGE_DESC",
    "IDENTITY_EDGES_DESC",
    "SCENARIOS_SEEN_DESC",
    "MESSAGES_DESC",
    "DECISIONS_DESC",
    "ORACLE_CALLS_DESC",
    "get_table",
    "list_tables",
]


@dataclass(frozen=True)
class TableDescriptor:
    """
    Frozen descriptor for a canonical CRV table.

    Attributes:
        name (TableName): Canonical table identifier (lower_snake serialized).
        columns (dict[str, str]): Mapping of lower_snake column_name -> dtype
            where dtype ∈ {"i64","f64","str","struct","list[struct]"}.
        partitioning (list[str]): Partition columns (always ["bucket"]).
        required (list[str]): Columns that must exist and be populated (non-null).
        nullable (list[str]): Columns permitted to contain nulls. Validations for
            combinations are enforced by Pydantic row models.
        version (SchemaVersion): Schema version pinned to crv.core.versioning.SCHEMA_V.

    Examples:
        >>> from crv.core.tables import get_table, TableName
        >>> desc = get_table(TableName.IDENTITY_EDGES)
        >>> "edge_kind" in desc.columns and "bucket" in desc.partitioning
        True

    Notes:
        - All column names are lower_snake (grammar policy).
        - required ⊆ columns; (required ∪ nullable) ⊆ columns; and required ∩ nullable = ∅
          are guarded by tests downstream.
        - Use list_tables() to iterate descriptors.
    """

    name: TableName
    columns: dict[str, str]  # "i64","f64","str","struct","list[struct]"
    partitioning: list[str]  # always ["bucket"]
    required: list[str]
    nullable: list[str]
    version: SchemaVersion


# -----------------------------------------------------------------------------
# Table descriptors
# -----------------------------------------------------------------------------

EXCHANGE_DESC = TableDescriptor(
    name=TableName.EXCHANGE,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "venue_id": "str",
        "token_id": "str",
        "exchange_event_type": "str",
        "side": "str",
        "quantity": "f64",
        "price": "f64",
        "actor_agent_id": "str",
        "counterparty_agent_id": "str",
        "baseline_value": "f64",
        "additional_payload": "struct",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "venue_id",
        "token_id",
        "exchange_event_type",
        "additional_payload",
    ],
    nullable=[
        "side",
        "quantity",
        "price",
        "actor_agent_id",
        "counterparty_agent_id",
        "baseline_value",
    ],
    version=SCHEMA_V,
)

IDENTITY_EDGES_DESC = TableDescriptor(
    name=TableName.IDENTITY_EDGES,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "observer_agent_id": "str",
        "edge_kind": "str",
        "subject_id": "str",
        "object_id": "str",
        "related_agent_id": "str",
        "token_id": "str",
        "edge_weight": "f64",
        "edge_sign": "i64",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "observer_agent_id",
        "edge_kind",
        "edge_weight",
    ],
    nullable=[
        "subject_id",
        "object_id",
        "related_agent_id",
        "token_id",
        "edge_sign",
    ],
    version=SCHEMA_V,
)

SCENARIOS_SEEN_DESC = TableDescriptor(
    name=TableName.SCENARIOS_SEEN,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "observer_agent_id": "str",
        "token_id": "str",
        "owner_status": "str",
        "peer_alignment_label": "str",
        "group_label": "str",
        "visibility_scope": "str",
        "channel_name": "str",
        "salient_agent_pairs": "list[struct]",
        "exchange_snapshot": "struct",
        "recent_affect_index": "f64",
        "salient_other_agent_id": "str",
        "context_hash": "str",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "observer_agent_id",
        "context_hash",
        "salient_agent_pairs",
        "exchange_snapshot",
    ],
    nullable=[
        "token_id",
        "owner_status",
        "peer_alignment_label",
        "group_label",
        "visibility_scope",
        "channel_name",
        "recent_affect_index",
        "salient_other_agent_id",
    ],
    version=SCHEMA_V,
)

MESSAGES_DESC = TableDescriptor(
    name=TableName.MESSAGES,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "sender_agent_id": "str",
        "channel_name": "str",
        "visibility_scope": "str",
        "audience": "struct",
        "speech_act": "str",
        "topic_label": "str",
        "stance_label": "str",
        "claims": "struct",
        "style": "struct",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "sender_agent_id",
        "channel_name",
        "visibility_scope",
        "audience",
        "speech_act",
        "topic_label",
        "claims",
        "style",
    ],
    nullable=[
        "stance_label",
    ],
    version=SCHEMA_V,
)

DECISIONS_DESC = TableDescriptor(
    name=TableName.DECISIONS,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "agent_id": "str",
        "chosen_action": "struct",
        "action_candidates": "list[struct]",
        "token_value_estimates": "struct",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "agent_id",
        "chosen_action",
        "action_candidates",
        "token_value_estimates",
    ],
    nullable=[],
    version=SCHEMA_V,
)

ORACLE_CALLS_DESC = TableDescriptor(
    name=TableName.ORACLE_CALLS,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "agent_id": "str",
        "engine": "str",
        "signature_id": "str",
        "persona_id": "str",
        "persona_hash": "str",
        "representation_hash": "str",
        "context_hash": "str",
        "value_json": "str",
        "latency_ms": "i64",
        # cache_hit is stored as 0/1 to keep dtypes within the allowed subset
        "cache_hit": "i64",
        "n_tool_calls": "i64",
        "tool_seq": "struct",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "agent_id",
        "engine",
        "signature_id",
        "persona_id",
        "persona_hash",
        "representation_hash",
        "context_hash",
        "value_json",
        "latency_ms",
        "cache_hit",
        "n_tool_calls",
        "tool_seq",
    ],
    nullable=[],
    version=SCHEMA_V,
)

# Registry
_TABLES: dict[TableName, TableDescriptor] = {
    EXCHANGE_DESC.name: EXCHANGE_DESC,
    IDENTITY_EDGES_DESC.name: IDENTITY_EDGES_DESC,
    SCENARIOS_SEEN_DESC.name: SCENARIOS_SEEN_DESC,
    MESSAGES_DESC.name: MESSAGES_DESC,
    DECISIONS_DESC.name: DECISIONS_DESC,
    ORACLE_CALLS_DESC.name: ORACLE_CALLS_DESC,
}


def get_table(name: TableName) -> TableDescriptor:
    """
    Look up a table descriptor by canonical name.

    Args:
        name (TableName): Canonical table name.

    Returns:
        TableDescriptor: Descriptor for the requested table.
    """
    return _TABLES[name]


def list_tables() -> list[TableDescriptor]:
    """
    Return all registered table descriptors.

    Returns:
        list[TableDescriptor]: List of all descriptors in registry order.
    """
    return list(_TABLES.values())
