"""
crv.viz — Read‑only transforms and dashboards over IO datasets.

## Responsibilities
- Provide composable, Polars‑first transforms for analysis of canonical tables.
- Offer chart/layer primitives and dashboards for common exploratory views.
- Never mutate canonical IO; read‑only by contract.

## Public API
- transforms — Helpers to assemble analysis frames from crv.io tables.
- layers — Altair layer primitives and encodings.
- dashboards — Ready‑to‑use dashboards that wire transforms and layers.
- networks — Network views for identity edges.
- timeseries — Time‑based views (e.g., value trajectories).
- distributions — Distribution plots over canonical metrics.

## Import DAG discipline
- Depends on: crv.io (Dataset scans), polars, altair (and stdlib).
- Must not write to IO or modify manifests.
- Must not import crv.world or crv.lab at runtime (only their artifacts via IO).

## Examples
```python
# Build a lightweight identity-edges view for a dashboard  # doctest: +SKIP
from crv.io import IoSettings, Dataset
import polars as pl
ds = Dataset(IoSettings(root_dir="runs/out"), run_id="demo_abcdef")
lf = (
    ds.scan("identity_edges", columns=["tick","observer_agent_id","edge_kind","token_id","edge_weight"])
      .filter(pl.col("edge_kind") == "self_to_object")
      .select(
          pl.col("tick").alias("t"),
          pl.col("observer_agent_id").alias("agent_id"),
          pl.col("token_id"),
          pl.col("edge_weight").alias("self_to_object_strength"),
      )
)  # doctest: +SKIP
df = lf.collect()  # doctest: +SKIP
```

## References
- [base](base.md)
- [dashboards](dashboards.md)
- [distributions](distributions.md)
- [events](events.md)
- [identity](identity.md)
- [layers](layers.md)
- [networks](networks.md)
- [save](save.md)
- [theme](theme.md)
- [timeseries](timeseries.md)
"""
