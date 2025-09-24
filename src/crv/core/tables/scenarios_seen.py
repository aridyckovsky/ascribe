"""
Canonical descriptor for the 'scenarios_seen' table.

Purpose:
- Observer-centric scenario context snapshots used in valuation/decision pipelines.

Schema:
- columns:
    bucket i64, tick i64, observer_agent_id str, token_id str,
    owner_status str, peer_alignment_label str, group_label str,
    visibility_scope str, channel_name str, salient_agent_pairs list[struct],
    exchange_snapshot struct, recent_affect_index f64, salient_other_agent_id str,
    context_hash str
- required:
    ["bucket","tick","observer_agent_id","context_hash","salient_agent_pairs","exchange_snapshot"]
- nullable:
    ["token_id","owner_status","peer_alignment_label","group_label","visibility_scope",
     "channel_name","recent_affect_index","salient_other_agent_id"]
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

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
