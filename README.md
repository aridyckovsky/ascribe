# Ascribe · Meaning → Value → Behavior with reproducible CIRVA models

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/license/mit)
Ascribe is a scalable social cognition framework for studying how context shapes internal representations and drives valuation and behavior. It provides typed contracts, deterministic simulation, and reproducible lab artifacts. This repository includes:

- CRV/CIRVA reference model under src/crv
  - core — grammar, schemas, table descriptors, hashing/serde, versioning, errors
  - io — canonical IO (append‑only, manifest‑tracked, Polars/Arrow‑first)
  - lab — EDSL‑based elicitation to build offline valuation policies
  - mind — pluggable oracle/compilation hooks (optional but recommended)
  - world — Mesa v3 simulation with deterministic artifacts
  - viz — Altair charts and dashboards (HTML/PNG export; used interactively in app)
- Streamlit application for exploring runs under src/app

_Transition note_: The distribution and repository are named ascribe. Python modules currently live under `crv.*` and the CLIs under `crv-*`. These remain supported for compatibility.

[Docs](https://docs.ascribe.live) · [Issues](https://github.com/aridyckovsky/ascribe/issues)

---

## Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick start (CLI)](#quick-start-cli)
- [Python API](#python-api)
- [Project layout](#project-layout)
- [Artifacts and data contracts](#artifacts-and-data-contracts)
- [Visualization](#visualization)
- [Determinism and testing](#determinism-and-testing)
- [Development](#development)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [License](#license)

---

## Overview

CRV/CIRVA is psychology‑first:

- Endowment lives inside the representation (self→object link).
- Valuation is a bounded readout from identity‑mediated triads.
- Decisions compare bounded value vs cost, with optional friction.

For mathematical specification and empirical signatures, see CONCEPT.md and the working manuscript.

---

## Installation

uv (recommended and supported)

```bash
uv venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
uv sync
```

Requirements

- Python 3.13+
- Optional (lab local runs): provider keys in .env (auto‑loaded by python‑dotenv)
- Optional (PNG export): vl-convert-python

---

## Quick start (CLI)

Simulation

```bash
uv run crv-abm-sim \
  --n 30 --k 1 --steps 100 --seed 123 --out out/run \
  [--policy path/to/policy.parquet] [--demo]
```

Parameter sweep

```bash
uv run crv-abm-sweep \
  --out out/sweep --steps 50 --seeds 101 102 \
  --gamma-tri 0.6 0.8 --beta-neg 1.2 --n 30 --k 1
```

Offline policy → sim (deterministic mock; no API keys)

```bash
uv run crv-lab build-policy --runs-root runs/policy_demo --mode mock --persona persona_baseline --model gpt-4o
RUN_DIR=$(ls -dt runs/policy_demo/* | head -1)
uv run crv-abm-sim --policy "$RUN_DIR/policies/policy_crv_one_agent_valuation_v0.1.0.parquet" --steps 10 --out out/policy_sim
```

---

## Python API

Basic simulation

```python
from crv.world import AgentParams, ModelParams, ExperimentParams, CRVModel

ap = AgentParams(k=1)
mp = ModelParams(n=10, k=1)
ep = ExperimentParams(steps=50, seed=123, out_dir="out/api_demo")
model = CRVModel(ap, mp, ep)

model.init_two_group_identity(cohesion=0.6, antagonism=-0.4)
for _ in range(ep.steps):
    model.step()

model.export_mesa_data()  # Parquet/CSV + metadata.json
```

Attach an offline policy

```python
from pathlib import Path
import crv.world.data as data

index = data.load_policy(Path("out/policy_demo/policy_crv_one_agent_valuation_v0.1.0.parquet"))
model.policy_index = index
model.policy_default = data.POLICY_DEFAULT
```

---

## Project layout

```
src/crv/
  world/   # Mesa model, schedule, config, events, data export (Polars)
  lab/     # EDSL orchestration → policy.parquet + manifest.json
  mind/    # Oracle/compilation scaffolding (optional)
  viz/     # Altair charts and dashboards; HTML/PNG export
  io/      # canonical IO (append-only, manifests, zstd partitions)
  core/    # zero‑IO contracts: grammar, schemas, tables, ids/typing, hashing/serde, versioning, errors

src/app/   # Streamlit UI shell and app-specific helpers

scripts/   # Reproducible demos (sim, policy+sim, sweeps, viz)
tests/     # CLI tests, step/determinism checks, viz spec tests
```

Boundary rules

- world does not import lab or mind; communicates via files or injected interfaces.
- lab has no runtime dependency on world/mind; produces tidy tables + policies.
- mind exposes engine‑agnostic oracles/compiled modules (optional).
- viz reads artifacts only; does not mutate core state.

---

## Artifacts and data contracts

Simulation outputs (under out/your_run/)

- agents_tokens.parquet, agents_tokens.csv
- model.parquet, model.csv
- metadata.json (seed, config hash, versions)

Policy parquet (from crv‑lab build‑policy)

- Columns: ctx_token_kind, ctx_owner_status, ctx_peer_alignment, persona, model, value_mean, value_sd, n
- Manifest JSON: survey_id, edsl_version, mode (edsl|edsl_fallback|mock), rows_raw, rows_policy, out_dir, policy_path, resolved_models, key‑presence flags

Time column

- Visualization groups by t; some summaries refer to step. If your agents_tokens lacks t, filter by step or adjust writer. Target is harmonized t.

Canonical IO (crv.io)

- Append‑only writes with atomic tmp→ready renames
- Per‑table manifest.json with bucket/tick stats for pruning and recovery
- Tick‑bucket partitioning (default 100) with zstd compression and ~128k row groups
- Strict schema validation against crv.core.tables
- Facade: from crv.io import IoSettings, Dataset

Quickstart

```python
import polars as pl
from crv.io import IoSettings, Dataset
from crv.core.grammar import TableName

settings = IoSettings(root_dir="out")
ds = Dataset(settings, run_id="20250101-000000")

df = pl.DataFrame({
    "tick": [0, 1, 2, 101],
    "observer_agent_id": ["A0", "A1", "A2", "A0"],
    "edge_kind": ["self_to_object"] * 4,
    "edge_weight": [0.0, 0.1, 0.2, 0.3],
})

summary = ds.append(TableName.IDENTITY_EDGES, df)
lf = ds.scan(TableName.IDENTITY_EDGES, where={"tick_min": 0, "tick_max": 120})
print(lf.collect())
```

---

## Visualization

Report export (HTML/PNG)

```bash
uv run crv-viz-report --run out/demo --out out/report.html --theme crv_light [--png report.png] [--cost 0.5]
```

Streamlit app

```bash
# Optional accelerator
uv add vegafusion

# Launch the Streamlit app
uv run crv-app --run out/demo_run

# Or direct Streamlit invocation with uv
uv run streamlit run src/app/ui.py -- --run out/demo_run
```

---

## Determinism and testing

- Fixed seeds and explicit config hashing; barrier semantics (valuations at t apply at t+1).
- Stable Polars schemas; artifacts include metadata.json.
- Tests cover CLI, step logic, and viz specifications.
- Core contracts validated under tests/core.

Coding standards

- Fully typed; `from __future__ import annotations`
- Google‑style docstrings (Args/Returns/Raises)
- Role‑specific modules; avoid catch‑all “utils” or “lib”

---

## Development

```bash
uv venv && source .venv/bin/activate
uv sync
uv run ruff check .
uv run mypy --strict
uv run pytest -q
```

---

## Documentation

- Build (strict): bash tools/generate_docs.sh
- Preview: uv run mkdocs serve

Sources and references

- Concept spec: CONCEPT.md
- Design and boundaries: src/crv/README.md
- Core contracts: src/crv/core/README.md
- IO/Lab/Viz READMEs are surfaced into the doc site via tools/build_docs.py
- Demo workflows: scripts/README.md

---

## Roadmap

- Harmonize time column naming (t vs step) across writers and viz
- Expand viz chart library and subgroup CEE small‑multiples
- Extend lab scenarios/personas; add schema tests
- Mind oracle compilation path (mock → compiled)
- Additional sweep utilities and artifact summarizers

---

## Citation

If you use Ascribe or the CRV/CIRVA model in academic work, please cite:

```bib
@misc{ascribe_framework,
  title        = {Ascribe: Framework for Context→Representation→Valuation Models},
  author       = {Dyckovsky, Ari M.},
  year         = {2025},
  howpublished = {\url{https://github.com/aridyckovsky/ascribe}}
}

@misc{crv_abm,
  title        = {CRV-ABM: Context→Representation→Valuation Agent-Based Model},
  author       = {Dyckovsky, Ari M.},
  year         = {2025},
  howpublished = {\url{https://github.com/aridyckovsky/ascribe}}
}
```

---

## License

MIT
