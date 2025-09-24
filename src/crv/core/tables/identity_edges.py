"""
Canonical descriptor for the 'identity_edges' table.

Purpose:
- Snapshot/delta rows of edges inside an agent’s internal representation as observed by an agent.
- Distinguishes edge families via RepresentationEdgeKind (edge_kind).

Schema:
- columns:
    bucket i64, tick i64, observer_agent_id str, edge_kind str,
    subject_id str, object_id str, related_agent_id str, token_id str,
    edge_weight f64, edge_sign i64
- required:
    ["bucket","tick","observer_agent_id","edge_kind","edge_weight"]
- nullable:
    ["subject_id","object_id","related_agent_id","token_id","edge_sign"]
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

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
