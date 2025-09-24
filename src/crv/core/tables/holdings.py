from __future__ import annotations

from crv.core.grammar import TableName
from crv.core.tables import TableDescriptor
from crv.core.versioning import SCHEMA_V

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
