"""
Canonical descriptor for the 'exchange' table.

Purpose:
- Generalized ownership-exchange events (trade/order/swap/gift/vote).

Schema:
- columns:
    bucket i64, tick i64, venue_id str, token_id str, exchange_event_type str,
    side str, quantity f64, price f64, actor_agent_id str, counterparty_agent_id str,
    baseline_value f64, additional_payload struct
- required:
    ["bucket","tick","venue_id","token_id","exchange_event_type","additional_payload"]
- nullable:
    ["side","quantity","price","actor_agent_id","counterparty_agent_id","baseline_value"]
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

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
