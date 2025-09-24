"""Canonical descriptor for the 'holdings' table.

Purpose:
- Quantity snapshot per (tick, agent_id, token_id). Optional per ADR-003
  when a conserved per-token resource is modeled.

Schema:
- columns:
    bucket i64, tick i64, agent_id str, token_id str, quantity i64
- required:
    ["bucket","tick","agent_id","token_id","quantity"]
- nullable:
    []
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) and ADR-003 for details.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

# Canonical holdings table descriptor (quantity snapshot per agent/token).
HOLDINGS_DESC = TableDescriptor(
    name=TableName.HOLDINGS,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "agent_id": "str",
        "token_id": "str",
        "quantity": "i64",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "agent_id",
        "token_id",
        "quantity",
    ],
    nullable=[],
    version=SCHEMA_V,
)
