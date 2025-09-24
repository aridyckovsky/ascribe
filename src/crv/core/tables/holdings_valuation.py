"""Canonical descriptor for the 'holdings_valuation' table.

Purpose:
- Per-tick valuation snapshot by (agent_id, token_id). Optional and additive per ADR-004.
  Echoes quantity and includes nullable valuation metrics (avg_unit_cost, mark_price, PnL)
  along with provenance strings (price_source, accounting_method).

Schema:
- columns:
    bucket i64, tick i64, agent_id str, token_id str, quantity i64,
    avg_unit_cost f64?, cost_value f64?, mark_price f64?, mark_value f64?,
    realized_pnl f64?, unrealized_pnl f64?, price_source str?, accounting_method str?
- required:
    ["bucket","tick","agent_id","token_id","quantity"]
- nullable:
    ["avg_unit_cost","cost_value","mark_price","mark_value","realized_pnl","unrealized_pnl",
     "price_source","accounting_method"]
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) and ADR-004 for details.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

# Canonical holdings_valuation table descriptor (quantity + optional valuation fields).
HOLDINGS_VALUATION_DESC = TableDescriptor(
    name=TableName.HOLDINGS_VALUATION,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "agent_id": "str",
        "token_id": "str",
        "quantity": "i64",
        "avg_unit_cost": "f64",
        "cost_value": "f64",
        "mark_price": "f64",
        "mark_value": "f64",
        "realized_pnl": "f64",
        "unrealized_pnl": "f64",
        "price_source": "str",
        "accounting_method": "str",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "agent_id",
        "token_id",
        "quantity",
    ],
    nullable=[
        "avg_unit_cost",
        "cost_value",
        "mark_price",
        "mark_value",
        "realized_pnl",
        "unrealized_pnl",
        "price_source",
        "accounting_method",
    ],
    version=SCHEMA_V,
)
