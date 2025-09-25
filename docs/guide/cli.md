# Command-Line Interface (CLI)

This guide summarizes the primary entry points for running simulations, eliciting policies, and exploring results. Commands are deterministic by design; configuration and seeds control reproducibility.

All examples assume uv is available. Prefix commands with `uv run` to ensure the project’s environment and dependencies are active.

## Overview of commands

- Simulation and sweeps
  - `crv-abm-sim` — run a single simulation instance using the CRV/CIRVA step function (see [crv.world][] and package modules).
  - `crv-abm-sweep` — orchestrate parameter sweeps across scenarios.
- Lab
  - `crv-lab` — build and audit per‑persona valuation policies for offline use (see [crv.lab][]).
- App and reports
  - `crv-app` — open the read‑only application to explore runs, charts, and KPIs (see [crv.viz][] and `app.main`).
  - `crv-viz-report` — generate a static report for a run (see [crv.viz][]).

These commands write Arrow‑friendly artifacts (see the Artifacts guide) and respect stability contracts indicated on API pages.

## crv-abm-sim

Run a single deterministic simulation.

Examples:

```bash
# Minimal demo
uv run crv-abm-sim --n 30 --k 1 --steps 100 --seed 123 --out out/run

# Use a prebuilt offline valuation policy (from the Lab)
uv run crv-abm-sim --policy runs/policy_demo/latest/policies/policy_crv_one_agent_valuation_v0.1.0.parquet \
  --steps 50 --seed 42 --out out/policy_run
```

Key flags (subject to change if marked experimental on API pages):

- `--steps` number of world steps to execute.
- `--seed` RNG seed for reproducibility.
- `--out` output directory for artifacts.
- `--policy` path to an offline valuation policy to plug into the loop.

See package modules under [crv.world][] for event schemas and stepping rules.

## crv-abm-sweep

Coordinate multiple runs across a parameter grid; produces a manifest of executed runs.

Example:

```bash
uv run crv-abm-sweep --grid config/sweeps/demo.toml --out out/sweeps/demo
```

Downstream tooling can discover and compare runs by reading manifests and per‑run artifacts (see [crv.io][]).

## crv-lab

Build and audit persona‑specific offline valuation policies.

Example (mock policy, no external services required):

```bash
uv run crv-lab build-policy --runs-root runs/policy_demo --mode mock \
  --persona persona_baseline --model gpt-4o
```

Artifacts:

- `policies/policy_*.parquet` files suitable for use with `crv-abm-sim`.
- A tidy audit summary to compare elicited policies across personas and scenarios.

See [crv.lab][] for policy interfaces and IO helpers.

## crv-app

Open the read‑only application to explore a run.

Example:

```bash
uv run crv-app --run out/run
```

The app discovers tables under the run directory and renders charts and KPIs. See the App guide for navigation and usage details, and package modules under [crv.viz][] and `app.main`.

## crv-viz-report

Export a static report for a run.

Example:

```bash
uv run crv-viz-report --run out/run --out out/run_report
```

Use this for sharing results without running the app. See [crv.viz][] for report composition.

## Reproducibility notes

- Always set `--seed` for repeatable trajectories.
- Write outputs to unique directories (`--out`) to keep runs isolated and comparable.
- Prefer offline policies for high‑throughput sweeps (see [crv.lab][]).
- Analyze with Arrow/Polars using the typed contracts in [crv.core][] and the Artifacts guide.

For deeper context on assumptions and cross‑cutting concepts, see the Concepts and Workflows guides.
