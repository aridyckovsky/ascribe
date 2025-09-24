"""
Frozen table descriptors for CRV canonical datasets (Parquet/Arrow-like).

Notes:
    - Descriptors declare column names/dtypes, partitioning, required/nullable
      columns, and the pinned schema version.
    - Column names are lower_snake.
    - Partitioning is always ["bucket"]; IO layers compute bucket as
      tick // TICK_BUCKET_SIZE.
    - Core is zero-IO (stdlib only); downstream IO (crv.io) materializes schemas.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from .decisions import DECISIONS_DESC
from .exchange import EXCHANGE_DESC
from .holdings import HOLDINGS_DESC
from .holdings_valuation import HOLDINGS_VALUATION_DESC
from .identity_edges import IDENTITY_EDGES_DESC
from .messages import MESSAGES_DESC
from .oracle_calls import ORACLE_CALLS_DESC
from .scenarios_seen import SCENARIOS_SEEN_DESC

__all__ = [
    "TableDescriptor",
    "EXCHANGE_DESC",
    "IDENTITY_EDGES_DESC",
    "SCENARIOS_SEEN_DESC",
    "MESSAGES_DESC",
    "DECISIONS_DESC",
    "ORACLE_CALLS_DESC",
    "HOLDINGS_DESC",
    "HOLDINGS_VALUATION_DESC",
    "get_table",
    "list_tables",
]


# Registry
_TABLES: dict[TableName, TableDescriptor] = {
    EXCHANGE_DESC.name: EXCHANGE_DESC,
    IDENTITY_EDGES_DESC.name: IDENTITY_EDGES_DESC,
    SCENARIOS_SEEN_DESC.name: SCENARIOS_SEEN_DESC,
    MESSAGES_DESC.name: MESSAGES_DESC,
    DECISIONS_DESC.name: DECISIONS_DESC,
    ORACLE_CALLS_DESC.name: ORACLE_CALLS_DESC,
    HOLDINGS_DESC.name: HOLDINGS_DESC,
    HOLDINGS_VALUATION_DESC.name: HOLDINGS_VALUATION_DESC,
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
