"""
CRV core IO-facing defaults.

Defines partitioning and compression defaults consumed by downstream IO layers. This
module is zero-IO and uses only the Python standard library.

Notes:
    - Downstream writers/readers compute bucket as ``tick // TICK_BUCKET_SIZE``.
    - Parquet/Arrow writers size row groups and set compression according to these values.
    - Changes to these constants should follow spec/ADR updates.

References:
    - specs: src/crv/core/.specs/spec-0.1.md, spec-0.2.md
    - ADR: src/crv/core/.specs/adr-2025-09-20-core-schema-0.1-and-graphedit-normalization.md
"""

from __future__ import annotations

__all__ = [
    "TICK_BUCKET_SIZE",
    "ROW_GROUP_SIZE",
    "COMPRESSION",
]

# Number of ticks grouped together for partitioning (e.g., bucket = tick // TICK_BUCKET_SIZE).
TICK_BUCKET_SIZE: int = 100

# Target row group size for IO backends (e.g., Parquet). Downstream writers may adapt around this.
ROW_GROUP_SIZE: int = 128 * 1024

# Default compression codec for persisted artifacts in IO layers that honor this contract.
COMPRESSION: str = "zstd"
