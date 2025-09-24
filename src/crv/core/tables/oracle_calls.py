"""
Canonical descriptor for the 'oracle_calls' table.

Purpose:
- LLM/tool invocation metadata and cache signals for deterministic audit.

Schema:
- columns:
    bucket i64, tick i64, agent_id str, engine str, signature_id str,
    persona_id str, persona_hash str, representation_hash str, context_hash str,
    value_json str, latency_ms i64, cache_hit i64, n_tool_calls i64, tool_seq struct
- required:
    ["bucket","tick","agent_id","engine","signature_id","persona_id","persona_hash",
     "representation_hash","context_hash","value_json","latency_ms","cache_hit",
     "n_tool_calls","tool_seq"]
- nullable:
    []
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- cache_hit is stored as 0/1 (i64) to conform to allowed dtypes in core tables.
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

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
        # TODO: We should expand allowed dtypes to include boolean
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
