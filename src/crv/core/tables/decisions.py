"""
Canonical descriptor for the 'decisions' table.

Purpose:
- Agent-level decisions per tick, including chosen action, action candidates, and
  token value estimates (if applicable).

Schema:
- columns:
    bucket i64, tick i64, agent_id str, chosen_action struct,
    action_candidates list[struct], token_value_estimates struct
- required:
    ["bucket","tick","agent_id","chosen_action","action_candidates","token_value_estimates"]
- nullable:
    []
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

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
