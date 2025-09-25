# Frequently Asked Questions (FAQ)

This FAQ addresses common questions about modeling assumptions, determinism, artifacts, and how to navigate the documentation. It emphasizes research‑first clarity with developer‑friendly pointers.

## What does “deterministic” mean in Ascribe?

Determinism means that given the same configuration and random seed, the CRV/CIRVA loop produces the same trajectory and artifacts byte‑for‑byte. Timing is barriered—signals computed at time t take effect at time t+1—so comparisons are well‑posed. See [crv.world][] and [crv.world.model][] for stepping; artifacts are summarized in the [Artifacts](artifacts.md) guide and schemas in [crv.core.tables][].

## How should I think about identity and affect?

Identity and affect are structured, typed relations (not opaque blobs). You will see explicit tables such as [crv.core.tables.identity_edges][], “other→object,” and value readouts. This enables policy design, invariants, and audits that generalize across experiments. See the [Concepts](concepts.md) guide and package modules in [crv.core][].

## What’s the quickest way to run and inspect a simulation?

Use the CLI:

- Run a sim: `uv run crv-abm-sim --steps 100 --seed 123 --out out/run`
- Open the app: `uv run crv-app --run out/run`

See the [CLI](cli.md) and [App](app.md) guides.

## How do I compare two ideas fairly?

Keep everything constant except the single assumption you’re testing. Reuse the same seed and policy; write outputs to distinct directories. Compare Arrow‑friendly tables directly (e.g., via Polars) and visualize with the app or a static report. See [Workflows](workflows.md).

## Where do I find the canonical API docs?

Start at the [API Reference overview](../api/index.md), then pick a package overview such as [crv.world][], [crv.lab][], [crv.io][], [crv.core][], [crv.viz][], or [crv.mind][]. Module pages are canonical; package pages are overviews that link down.

## What do the stability banners mean?

- Stable API: intended to persist; changes will be additive.
- Experimental API: available for use; may change as research hardens.
- Unstable API: subject to change without notice.

The banner appears at the top of each package/module page when configured. See stability metadata under `docs/metadata/stability.yml`.

## Can I run sweeps without external services?

Yes. Build offline valuation policies with [crv.lab][] (e.g., mock mode) and reuse them across scenarios. This keeps experiments fast and comparable. See [crv.lab][] and [CLI](cli.md).

## How should I cite or archive results?

Export a static report with `crv-viz-report` and archive the run directory (including `metadata.json`). Include links to the API pages you rely on so stability is clear.

## How do cross‑references work in these docs?

Cross‑references use automatic linking (mkdocs‑autorefs). When you mention a symbol or page like [crv.world.events][] or [Artifacts](artifacts.md), links resolve across pages without manual anchors.

## Where can I learn the broader research context?

- Start with [Getting Started](getting-started.md) and [Concepts](concepts.md).
- Review the API package overviews from the [API Reference overview](../api/index.md).
- For broader trajectory notes, see materials under `concept_docs/` in the repository.
