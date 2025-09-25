# Concepts

This guide states the core ideas behind Ascribe in an academic, research‑first tone while remaining developer‑friendly. It explains how context, identity, and valuation are formalized and how determinism supports careful comparison and replay.

## CIRVA: a barriered loop

Ascribe explicitly implements the CIRVA loop:

- Context → Interpret → Representation → Valuation → Action/Communication

A central barrier guarantees that signals computed at time t only affect the world at time t+1. This preserves determinism and supports exact replay. The world kernel advances this loop; see [crv.world][] and [crv.world.model][] for the step function and event types, and the core contracts in [crv.core][].

- Interpretation turns observations into typed, inspectable appraisals.
- Representation updates a structured internal graph of identity and affect.
- Valuation reads bounded values from that representation to score options.
- Actions and communications are emitted on channels with scope and optional delay.

The loop is auditable end‑to‑end: all inputs, intermediate representations, and outputs are recorded as Arrow‑friendly artifacts.

## Identity and affect as structure

Agents carry a structured state that includes:

- identity edges (self→other ties),
- other→object stances,
- object→object valence traces,
- self→object “endowment.”

These are explicit tables and typed objects, not opaque blobs. See the contracts and tables under [crv.core.tables][] and related modules (for example, [crv.core.tables.identity_edges][], [crv.core.tables.holdings][], [crv.core.tables.holdings_valuation][]).

Because state is typed, you can program policies, invariants, and audits that rely on the same representation across experiments.

## Channels, scope, and delay

Observations and communications flow over channels with:

- scope (public, group, room, direct),
- optional delay (deferring visibility by steps),
- topology rules that bound propagation.

These rules are explicit and testable. See [crv.world.events][] for event schemas and [crv.world.observation_rules][] for visibility and topology.

## Determinism and replay

Determinism is a design constraint:

- barriered timing isolates t from t+1,
- pure table writes and Arrow outputs enable byte‑for‑byte replay,
- configured random seeds ensure reproducible sweeps.

As a result, you can vary one assumption at a time, attribute differences to that change, and re‑run to verify.

## Stability and evolution

Interfaces evolve along a clear stability axis:

- Stable APIs are intended to persist with additive changes.
- Experimental APIs are available for use but may change as research hardens.
- Unstable APIs can change without notice.

Stability status is shown at the top of each API page. See [API Reference](../api/index.md) and package overviews such as [crv.core][], [crv.io][], [crv.lab][], [crv.mind][], [crv.viz][], and [crv.world][].

## Developer notes

- Start from “Getting Started,” then open a package overview like [crv.world][] or [crv.core][].
- Use the CLI for quick experiments (see the CLI guide), then inspect artifacts with your analysis tool.
- Prefer explicit, typed transformations over implicit side‑effects; this aligns with the barriered loop and keeps runs auditable.
