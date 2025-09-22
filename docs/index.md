# Ascribe: Modeling how value is built, shared, and measured

Ascribe helps you study how people and communities come to value things—ideas, art, information, policies—by running transparent, repeatable experiments with simulated agents and real data. We call the approach CRV: Context → Representation → Valuation.

- Context: what a person sees and experiences.
- Representation: how they understand, remember, and reason about it.
- Valuation: what they decide, choose, or assign value to.

Ascribe turns these into clear, auditable experiments you can run, share, and reproduce.

## Who is this for?

- Social scientists and policy researchers exploring norms, trust, polarization, fairness, or culture.
- Product and platform teams evaluating incentives, ranking, and reputation systems.
- Journalists, educators, and the public seeking transparent “what if” experiments.
- Advanced programmers who want typed, deterministic, and testable pipelines.

No advanced math or ML background is required to start. Power users can go deep.

## What kinds of questions can you study?

- How do rating systems change what people value over time?
- When do communities converge on shared beliefs—and when do they split?
- How do visibility rules (who sees what) shape fairness and outcomes?
- Which incentives encourage quality contributions without gaming?
- How do simple memory or bias assumptions produce real‑world patterns?
- Can we audit an experiment end‑to‑end and replay the exact results?

### Core concepts

- Agents and worlds: Agents are people or roles; a world is the environment they act in.
- Context: What an agent can observe (feeds, neighbors, prompts, signals).
- Representation: How an agent processes context (attention, memory, heuristics).
- Valuation: The choices agents make (like, share, trust, spend, rank, allocate).
- Experiments as recipes: You define personas, scenarios, and tasks like a lab protocol.
- Provenance and replay: Every run produces artifacts you can audit and rerun exactly.

### A quick example

Imagine you’re studying how people come to value artworks.

1. Define a persona: “Newcomer” with limited attention and short memory.
2. Set the context: A feed shows artworks with titles, creators, and some social signals.
3. Representation: The persona remembers a few items and weighs signals with a small bias.
4. Valuation: The persona picks 3 artworks to “feature” each day.
5. World rule: Featured items become a bit more visible tomorrow (feedback loop).

Run the experiment for 30 days. Inspect the outputs:

- What gets featured? Stable favorites or fads?
- Are certain creators systematically amplified?
- Do small initial differences snowball into large inequalities?

You can replay the exact run, change one assumption (e.g., memory length), and compare.

## What you get out of the box

- Reproducible run bundles: Append‑only manifests, hashes, and versioned artifacts.
- Data you can analyze: Parquet/JSON outputs suitable for R/Python/journal notebooks.
- Built‑in dashboards: Read‑only visualizations to explore outcomes and provenance.
- Guardrails: Clear separation between definitions (the recipe) and results (the evidence).

### How Ascribe works

1. Describe your experiment (personas, scenarios, tasks) in a small typed language.
2. Run a deterministic simulation of agents in a world with simple, transparent rules.
3. Collect artifacts (inputs, outputs, decisions) with strong provenance guarantees.
4. Visualize and audit: inspect what happened and why, step by step.
5. Share and reproduce: others can rerun the exact bundle or modify a single assumption.

### Try it now (5 minutes)

Follow the [Getting Started](guide/getting-started.md) guide for a minimal walkthrough:

When you’re ready, explore the sample runs in this repo and open the dashboards.

### Modules in human terms

- [Core](/api/crv/core/) (definitions and guarantees): names, schemas, IDs, hashing, versioning, errors.
- [IO](/api/crv/io/) (evidence and bundles): append‑only manifests, partitioning, validation, replay.
- [Lab](/api/crv/lab/) (your experiment design): personas, scenarios, typed tasks, probes, audits.
- [Mind](/api/crv/mind/) (reasoning strategies): typed cognition; plug in or compare simple policies.
- [World](/api/crv/world/) (the stage): event queues, observation/visibility rules, valuation pipeline.
- [Viz](/api/crv/viz/) (looking at results): read‑only dashboards over the artifacts you produced.

## How Ascribe keeps you honest

- Deterministic by default: runs are replayable bit‑for‑bit.
- Append‑only provenance: manifests index all inputs/outputs and their hashes.
- No hidden state: decisions are recorded and traceable.
- Clear boundaries: “recipe” definitions are separate from the “results” they produce.
- Tests and validation: schemas and flows are checked end‑to‑end.

## Glossary

- Agent: An actor with limited attention, memory, and simple rules.
- Context: What an agent can see at a given time.
- Representation: How the agent encodes, remembers, or reasons about context.
- Valuation: A choice, score, ranking, allocation, or other value signal.
- Scenario: The environment and schedule an agent is placed in.
- Run bundle: The complete, hashed record of an experiment run.
- Provenance: The “chain of custody” for data and decisions.

More to come.

## Frequently asked questions

- Is this machine learning?
  **Not necessarily. Start with simple, transparent rules. You can swap in learned policies later if needed.**

- Can I analyze results in R/Python?
  **Yes. Artifacts are saved as Parquet/JSON for standard data tools.**

- Can others reproduce my study?
  **Yes. Share the run bundle; they can replay or change one assumption and compare.**

- Do I need to know programming?
  **You can begin by running included experiments and exploring dashboards. To design new experiments, some scripting is helpful; we keep the definitions small and readable.**

## Next steps

- Start here: [Getting Started](guide/getting-started.md)
- Browse APIs when you need details: [Core](/api/crv/core/) · [IO](/api/crv/io/) · [Lab](/api/crv/lab/) · [Mind](/api/crv/mind/) · [World](/api/crv/world/) · [Viz](/api/crv/viz/)
- Explore sample runs and dashboards in the repository.

## Project status and citation

Ascribe is evolving; interfaces may change as we expand examples and audits.
Please cite the project and include run bundle IDs when reporting results.
