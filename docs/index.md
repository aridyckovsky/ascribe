# CRV Agents

CRV (Context → Representation → Valuation) is a deterministic, auditable platform for studying social construction of value with agent‑based simulations, typed cognition, and reproducible lab artifacts. This site documents the modules, APIs, and guides for working with the CRV stack.

## At a Glance

- Core contracts and grammar (zero‑IO): enums/EBNF, schemas, table descriptors, hashing/serde, IDs, errors, versioning.
- Canonical IO layer (append‑only, manifests, partitioning, validation).
- Lab (personas, scenarios, typed EDSL tasks, offline per‑persona policies, probes/audits).
- Mind (typed cognition with DSPy; ReAct/mem0/GEPA integration plans).
- World (ABM kernel with queues, observation rules, valuation pipeline).
- Viz (read‑only dashboards over Parquet artifacts).

## Quick Links

- [Getting Started](guide/getting-started.md)
- [Core](src/crv/core/README.md)
- [IO](src/crv/io/README.md)
- [Lab](src/crv/lab/README.md)
- [Mind](src/crv/mind/README.md)
- [World](src/crv/world/README.md)
- [Viz](src/crv/viz/README.md)

## Repository Highlights

- Strict data contracts and provenance across boundaries (JSON/Parquet).
- t+1 barrier and deterministic replay.
- Append‑only manifests and Run Bundle indexing.
- Tests for grammar, schemas, IO, and end‑to‑end flows.

To build this site locally (strict):

```bash
bash tools/generate_docs.sh
open site/index.html
```

For a minimal code walkthrough, see the Getting Started guide.
