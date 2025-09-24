from __future__ import annotations

from crv.core.grammar import TableName
from crv.core.tables import TableDescriptor
from crv.core.versioning import SCHEMA_V

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
