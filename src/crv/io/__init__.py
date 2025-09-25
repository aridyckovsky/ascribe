"""
crv.io — Canonical IO layer for CRV datasets.

## Responsibilities
- Provide a Polars/Arrow-first IO layer that materializes canonical tables defined in crv.core.tables.
- Guarantee append-only semantics, atomic tmp→ready file renames, per-table manifests, tick-bucket partitioning, and lightweight schema validation against crv.core descriptors.
- Keep crv.core as the single source of truth for enums, schemas, table descriptors, IDs, and versioning.

## Public API
- IoSettings — Configuration for IO behavior (defaults sourced from crv.core.constants).
- Dataset — Facade bound to a run that supports append/scan/read/manifest operations.

## Source of truth and dependencies
- crv.core.grammar.TableName is the canonical table name enum; docstrings and type hints refer to it.
- crv.core.tables provides TableDescriptor instances (columns/dtypes/required/nullable/partitioning=["bucket"]/version=SCHEMA_V).
- crv.core.ids provides typed identifiers (e.g., RunId) used in annotations and docs.
- crv.core.versioning provides SCHEMA_V embedded in Parquet key-value metadata.
- crv.core.errors and crv.core.schema define core normalization/validation semantics; crv.io raises Io* errors for IO-layer failures.

## Import DAG discipline
- Depends only on stdlib, polars/pyarrow (and optionally fsspec later), and crv.core.*.
- MUST NOT import higher layers: world, mind, lab, viz, or app.

## Examples
```python
import polars as pl
from crv.io import IoSettings, Dataset
from crv.core.grammar import TableName

settings = IoSettings(root_dir="out", tick_bucket_size=100)  # doctest: +SKIP
ds = Dataset(settings, run_id="20250101-000000")  # doctest: +SKIP
df = pl.DataFrame({  # doctest: +SKIP
    "tick": [0, 1, 2, 101],
    "observer_agent_id": ["A0", "A1", "A2", "A0"],
    "edge_kind": ["self_to_object"] * 4,
    "edge_weight": [0.0, 0.1, 0.2, 0.3],
})
ds.append(TableName.IDENTITY_EDGES, df)  # doctest: +SKIP
```

## Notes
- IO write path: tmp parquet → fsync → os.replace(tmp, final) on the same filesystem for atomicity.
- Partitioning: bucket = tick // IoSettings.tick_bucket_size; bucket dirs are zero‑padded (e.g., bucket=000123).
- Manifests: JSON per table tracks partitions and parts and is used for pruning in scan().

## References
- [artifacts](artifacts.md)
- [config](config.md)
- [dataset](dataset.md)
- [errors](errors.md)
- [fs](fs.md)
- [manifest](manifest.md)
- [paths](paths.md)
- [read](read.md)
- [run_manifest](run_manifest.md)
- [validate](validate.md)
- [write](write.md)
"""

from __future__ import annotations

from .config import IoSettings
from .dataset import Dataset

__all__ = [
    "IoSettings",
    "Dataset",
]
