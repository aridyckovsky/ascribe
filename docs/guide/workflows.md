# Workflows

This guide presents recommended research and development workflows for using Ascribe in a deterministic, reproducible manner. The emphasis is on careful comparison, sweeps, and replayability.

## Research workflow: from hypothesis to evidence

1. Formulate a question with a falsifiable claim.

- Example: “Public endorsements amplify attachment more than private exchanges.”
- Identify what to measure (e.g., changes in holdings, value readouts, identity edges).

2. Configure the world, personas, and channels.

- Specify observation scopes (public/group/room/direct) and delays; see [crv.world][] and [crv.world.events][].
- Choose or elicit valuation policies; see [crv.lab][].

3. Run a deterministic baseline.

- Use `crv-abm-sim` with an explicit `--seed` and unique `--out` path.
- Inspect artifacts; see the [Artifacts](artifacts.md) guide and [crv.io][] for paths and manifests.

4. Perform controlled variations (ablations).

- Change one assumption at a time.
- Re‑run with the same seed and compare Arrow‑friendly tables.

5. Report and archive.

- Produce a static report with `crv-viz-report`, and archive the run directory.
- Link to canonical API pages for the symbols you depend on (stability annotations apply).

## Development workflow: iterate without breaking determinism

1. Start small with mock policies.

- Use [crv.lab] to build offline valuation policies for fast iteration.
- Plug policies into `crv-abm-sim` to accelerate sweeps.

2. Maintain explicit seeds and manifests.

- Treat `metadata.json` and run directory layout as the source of provenance.
- Avoid implicit global state; prefer typed transformations in [crv.core][].

3. Write and run tests alongside docs.

- Tests under `tests/` encode key invariants (IO contracts, schema guards, visibility rules).
- Keep changes additive for stable APIs; experimental areas are marked on API pages.

4. Visualize and compare frequently.

- Explore with `crv-app` for live charts and KPIs (see [App](app.md)).
- Use reports to snapshot progress and share results.

## Sweeps: structured exploration

Parameter sweeps help map how outcomes depend on assumptions.

- Use `crv-abm-sweep` to run a grid; keep output runs isolated (`--out out/sweeps/...`).
- Prefer a single RNG seed per scenario for direct comparability.
- Summarize outcomes using Polars against stable table schemas in [crv.core.tables][].

Typical sweep plan:

- Define parameter grid (e.g., visibility scopes, delay patterns).
- Reuse the same offline policy to isolate world dynamics from valuation changes.
- Compute simple KPIs (e.g., Gini on holdings, mean value readouts, coalition counts) per run.

## Replay and audit

Determinism supports byte‑for‑byte replay.

- Re‑run with the same configuration + seed to reproduce a trajectory exactly.
- Audit invariants directly over Arrow tables (e.g., conservation constraints, bounds on value score).
- Keep a small library of invariant checks in your analysis environment to accompany experiments.

## Practical checklists

Before running:

- Specify seed, output directory, and relevant policy path.
- Confirm stability of the APIs you rely on via the banners on package/module pages.

After running:

- Verify artifacts exist and schemas match expectations (see [crv.core.tables][]).
- Record KPIs and links to the run in your notes or issue tracker.

## Cross‑references

- CLI: see the [CLI](cli.md) guide for common invocations.
- Artifacts: see [Artifacts](artifacts.md) for file layout and schemas.
- Packages: start from the [API Reference](../api/index.md) overview and browse [crv.world][], [crv.lab][], [crv.io][], [crv.core][], [crv.viz][], and [crv.mind][].
