# Artifacts

This guide summarizes the deterministic artifacts emitted by Ascribe runs and how they support reproducible, audit‑ready research. Tables are Arrow‑friendly and stable across runs that share configuration and seeds.

## What is recorded

A run writes a minimal, typed record of the CRV/CIRVA loop:

- Model snapshot
  - `model.parquet` with `metadata.json` describing configuration, seeds, and environment.
- Event log
  - `events.parquet` capturing observations and actions, including channel, scope, and delay; see [crv.world.events][].
- Agent signals
  - `agents_tokens.parquet` with step‑stamped per‑agent, per‑object signals and readouts such as value scores and holdings.
- Relations
  - Tables describing identity and affect structure, for example [crv.core.tables.identity_edges][], [crv.core.tables.holdings][], [crv.core.tables.holdings_valuation][], and other derived relations.

Each file is append‑only within a run and can be joined by time and identifiers for analysis.

## Structure and typing

Artifacts mirror the typed contracts in [crv.core][]. A few examples (see module pages for full schemas):

- Identity edges: who relates to whom and how strongly; see [crv.core.tables.identity_edges][].
- Holdings and valuations: inventory state and bounded value readouts; see [crv.core.tables.holdings][] and [crv.core.tables.holdings_valuation][].
- Exchange and messages: world‑level events; see [crv.core.tables.exchange][] and [crv.core.tables.messages][].

This correspondence allows you to write invariant checks and audits against the same types that implementations use.

## IO and manifests

Paths, bucket math, and on‑disk layout are managed in [crv.io][] and [crv.io.config][]. A run’s directory is self‑contained:

- `metadata.json` serves as the minimal manifest of configuration used.
- Data files are placed in predictable subpaths to enable discovery and tooling.

See tests under `tests/io/` for contract expectations and path composition.

## Determinism and comparison

Because both state and timing are explicit, two runs with the same configuration and seed produce byte‑for‑byte comparable artifacts. This supports:

- Replay: reproduce a trajectory exactly for inspection and debugging.
- Ablation: change one assumption at a time and attribute deltas to that change.
- Audits: assert invariant properties over relations and outcomes.

## Practical tips

- Use `uv run crv-app --run <path>` to explore a run interactively (see the App guide).
- Read tables with Polars or Arrow; schemas are stable and typed.
- For quick sweeps, build an offline valuation policy in [crv.lab][] and reuse it across scenarios; outputs remain comparable.
