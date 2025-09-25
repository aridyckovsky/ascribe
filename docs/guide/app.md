# App

This guide describes the read‑only application for exploring runs, charts, and KPIs. The app renders Arrow‑friendly artifacts produced by the CRV/CIRVA loop and is designed for deterministic, reproducible inspection.

## Launch

Open a run directory:

```bash
uv run crv-app --run out/run
```

The app discovers tables under the run path and loads typed schemas aligned with [crv.core][] and [crv.io][]. It presents a consistent navigation surface so you can compare runs side‑by‑side.

## Navigation

- Overview
  - Summary KPIs, metadata snapshot (`metadata.json`), and configuration context.
- Identity and relations
  - Graph‑based views of identity edges and other relations; see [crv.core.tables.identity_edges][] and related tables.
- Agent signals
  - Time‑stamped per‑agent, per‑object readouts (e.g., value scores, holdings) from `agents_tokens.parquet`.
- Events
  - Observations and actions with channel, scope, and delay; see [crv.world.events][].
- Artifacts
  - Direct links and schema hints for files to support external analysis; see the [Artifacts](artifacts.md) guide.

The app reads structures rather than inferring semantics, which preserves determinism and reduces accidental coupling.

## KPIs and charts

Charts are oriented toward comparative analysis:

- Distributions and trajectories of value readouts,
- Inventory and exchange dynamics,
- Identity graph snapshots and evolution.

Visualizations draw from [crv.viz][] and related helpers; APIs marked experimental may change.

## Reproducibility and provenance

- The app treats the run directory as the source of truth; it does not mutate artifacts.
- Deterministic outputs enable byte‑for‑byte replay and like‑for‑like visual comparison.
- Consider exporting a static report with `crv-viz-report` when sharing results outside the live app (see [crv.viz][]).

## Tips

- Keep one app window per run for focused inspection; use separate windows to compare runs.
- Use explicit seeds and unique `--out` paths when generating runs (see the [CLI](cli.md) guide).
- Check stability banners on API pages (e.g., [crv.viz][], `app.main`) to understand evolution status.
