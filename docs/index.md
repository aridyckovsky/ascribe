# Ascribe

Ascribe is a way to make psychological assumptions about value explicit inside AI agents and to observe how those assumptions play out in shared worlds. Agents perceive context, interpret what they see, update a structured internal representation (identity, affect, memory, attention), read out value, and then act or communicate. By running these simulations deterministically, we can learn about the conditions under which values converge, diverge, or polarize&mdash;and use those lessons to design real multi‑agent tests with people more safely and thoughtfully.

Ascribe names this modeling loop CRV/CIRVA: Context → (Interpret) → Representation → Valuation → (Action).

\*Note: This is an in-progress, very early-stage documentation site. All guidance and API are **unstable**.

## Contents

- [What you can do with Ascribe](#what-you-can-do-with-ascribe)
- [Why this matters](#why-this-matters)
- [How it works (CRV/CIRVA)](#how-it-works-crvcirva)
- [What’s in the box today](#whats-in-the-box-today)
- [Try it quickly](#try-it-quickly)
- [Outputs at a glance](#outputs-at-a-glance)
- [Learn more](#learn-more)

## What you can do with Ascribe

- Describe how agents see the world (channels, visibility, timing), how they interpret it, and how that shapes their internal representation.
- Explore how identity, affect, memory, and attention drive valuations and behavior over time.
- Compare rules for visibility and communication (e.g., public vs group vs DM) and observe subgroup divergence.
- Prototype incentives and exchange rules and see how they interact with identity and affect.
- Use the results to plan human or real multi‑agent tests: which conditions to vary, what to measure, and how to pre‑register analyses.

## Why this matters

Psychological assumptions are often implicit. Ascribe makes them concrete and auditable. By running AI agents with human‑inspired cognitive architectures in simulated worlds, we can generate hypotheses about social dynamics&mdash;like when endorsements amplify attachment, when groups diverge under different visibility rules, or how coalitions shape value readouts. Those simulations help decide which systems are promising to test with people, how to stage those tests, and what to measure.

## How it works (CRV/CIRVA)

At the core is a simple, repeatable loop for each agent:

- Context  
  Agents receive events routed by channel and visibility (e.g., public, group, room, DM) with optional delays.

- Interpret  
  Agents turn observations into typed, and therefore inspectable, interpretations that lead to appraisals.

- Representation  
  Agents update a structured internal graph of identity and affect (e.g., self→object “endowment,” self→other ties, perceived other→object stances, object→valence traces). The focus is on keeping these state changes explicit and replayable.

- Valuation  
  Agents read out bounded values from their representation to score options.

- Action/Communication  
  Agents take actions (e.g., acquire/relinquish/relate/endorse/exchange) or send typed messages (speech acts). The world logs what happened.

- Deterministic timing  
  What is computed during time $t$ is applied at time $t+1$, making runs deterministic and suitable for careful comparison.

This loop is designed for narrative clarity first&mdash;so we can tell a coherent story about why an agent did what it did&mdash;while remaining rigorous enough to support reproducible analysis.

## What’s in the box today

- A deterministic world kernel that executes the loop above and writes reproducible artifacts.
- Typed interfaces for agent cognition so interpretations, patches to internal state, and decisions remain explicit.
- A lightweight "lab" path to elicit per‑persona valuation policies over scenarios for fast sweeps without external services.
- A read‑only visualization app for exploring runs and seeing how values and identity evolve.

As the project evolves, the community may extend cognitive modules (e.g., bounded tool use, per‑agent memories), add richer visibility and coalition structures, and broaden exchange mechanisms—while preserving the same guarantees about determinism and explicit boundaries.

## Try it quickly

Simulate a small run:

```bash
uv run crv-abm-sim --n 30 --k 1 --steps 100 --seed 123 --out out/run
```

Open the app on that run:

```bash
uv run crv-app --run out/run
```

Build a mock offline policy (no external keys required), then use it in a sim:

```bash
uv run crv-lab build-policy --runs-root runs/policy_demo --mode mock --persona persona_baseline --model gpt-4o
uv run crv-app --run out/run
```

## Outputs at a glance

Runs produce Arrow‑friendly tables you can analyze in notebooks or view in the app. Typical files include:

- `agents_tokens.parquet` (time‑stamped per‑agent, per‑object signals such as $s_{io}$, value_score, holdings)
- `model.parquet` and `metadata.json` (configuration snapshots)
- `events.parquet` (actions vs observations with channel/scope/delay), `relations.parquet` ($i\to j$), `other_object.parquet` ($i\to j$ on $o$), `object_object.parquet` ($o\to o$)
- Optional lab artifacts: `policies/policy_*.parquet`, `lab/tidy.parquet`

Files are written append‑only and can be replayed for careful comparison across runs.

## Learn more

- Quick guide: [Getting Started](guide/getting-started.md)
- Explore the app and charts, then open the tables in your favorite analysis tool.
- When you’re ready to dig deeper: visit the API docs for World, Lab, Mind, IO, and Core under `/api/crv/...`, and read the conceptual notes in `concept_docs/` for the broader research trajectory.
