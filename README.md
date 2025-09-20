# CRV‑ABM · Context → Representation → Valuation

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/license/mit)

CRV‑ABM is a typed, reproducible agent‑based modeling stack for value formation. It models how context updates an agent’s internal representation (self, others, objects, valence) and reads out valuation as a bounded function of that representation.

- world — Mesa v3 simulation with deterministic artifacts
- lab — EDSL‑based elicitation to build offline valuation policies
- viz — Altair charts and dashboards
- mind — pluggable oracle/compilation hooks (optional but recommended)

---

## Contents

- [Overview](#overview)
- [Getting started](#getting-started)
- [Usage (CLI)](#usage-cli)
- [Python API](#python-api)
- [Artifacts and contracts](#artifacts-and-contracts)
- [Visualization](#visualization)
- [Architecture](#architecture)
- [Determinism and testing](#determinism-and-testing)
- [Development](#development)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [Citation](#citation)
- [License](#license)

---

## Overview

CRV is psychology‑first:

- Endowment lives inside the representation (the self→object link).
- Valuation is a bounded readout from identity‑mediated triads (not an add‑on premium).
- Decisions compare bounded value vs cost with optional friction.

For the mathematical specification and empirical signatures, see CONCEPT.md and working manuscript.

---

## Getting started

Option A — uv (recommended)

```bash
uv venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
uv sync
```

Option B — pip (editable install)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Requirements

- Python 3.13+
- Optional (lab local runs): OPENAI_API_KEY and other provider keys in .env (auto‑loaded by python‑dotenv)
- Optional (PNG export): vl-convert-python

---

## Usage (CLI)

Simulation

```bash
uv run crv-abm-sim \
  --n 30 --k 1 --steps 100 --seed 123 --out out/run \
  [--policy path/to/policy.parquet] [--demo]
```

- Policy parquet columns: ctx_token_kind, ctx_owner_status, ctx_peer_alignment, persona, model, value_mean
- Determinism: valuations computed at t apply at t+1 (barrier semantics)

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

Visualization

```bash
uv run crv-viz-report --run out/run --out report.html --theme crv_light [--png report.png] [--cost 0.5]
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

## Artifacts and contracts

Simulation outputs (under out/your_run/)

- agents_tokens.parquet, agents_tokens.csv
- model.parquet, model.csv
- metadata.json (seed, config hash, versions)

Policy parquet (from crv‑lab build‑policy)

- Columns: ctx_token_kind, ctx_owner_status, ctx_peer_alignment, persona, model, value_mean, value_sd, n
- Manifest JSON: survey_id, edsl_version, mode (edsl|edsl_fallback|mock), rows_raw, rows_policy, out_dir, policy_path, resolved_models, key‑presence flags

Time column

- Visualization groups by t; some summaries refer to step. If your agents_tokens lacks t, filter by step or adjust writer. Target is harmonized t.

---

## Visualization

```bash
uv run crv-viz-report --run out/demo --out out/report.html --theme crv_light [--png report.png] [--cost 0.5]
```

- Inputs: agents_tokens.parquet (required), optional cee.parquet
- PNG export requires vl-convert-python

### Streamlit (default for large data)

- Server-backed interactive app with Polars-first transforms and small Altair payloads.
- Rendering uses Streamlit’s Altair API with our theme:
  - st.altair_chart(chart, theme=None, use_container_width=True)
- Optional accelerator: if VegaFusion is installed, the app attempts to enable it via:
  - import altair as alt; alt.data_transformers.enable("vegafusion")

Usage:

```bash
# Optional accelerator
uv add vegafusion

# Launch the Streamlit app
uv run crv-viz-app --run out/demo_run

# Or direct Streamlit invocation
uv run streamlit run src/crv/viz/app/app.py -- --run out/demo_run
```

---

## Architecture

```
src/crv/
  world/   # Mesa model, schedule, config, events, data export (Polars)
  lab/     # EDSL orchestration → policy.parquet + manifest.json
  mind/    # Oracle/compilation scaffolding (optional)
  viz/     # Altair charts and dashboards; HTML/PNG export
  core/    # zero‑IO contracts: grammar, schemas, tables, ids/typing, hashing/serde, versioning, errors

scripts/   # Reproducible demos (sim, policy+sim, sweeps, viz)
tests/     # CLI tests, step/determinism checks, viz spec tests
```

Boundary rules

- world does not import lab or mind; communicates via files or injected interfaces.
- lab has no runtime dependency on world/mind; produces tidy tables + policies.
- mind exposes engine‑agnostic oracles/compiled modules (optional).
- viz reads artifacts only; does not mutate core state.

---

## Determinism and testing

- Fixed seeds and explicit config hashing; barrier semantics (valuations at t apply at t+1).
- Stable Polars schemas; artifacts include metadata.json.
- Tests cover CLI, step logic, and viz specifications.
- Core contracts validated under tests/core (naming invariants, identity edge combination rules, table descriptor contracts, versioning helpers).

Coding standards

- Fully typed; `from __future__ import annotations`.
- Google‑style docstrings (Args/Returns/Raises) with brief examples.
- Role‑specific modules; avoid catch‑all “utils” or "lib".

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

## Roadmap

- Harmonize time column naming (t vs step) across writers and viz
- Expand viz chart library and subgroup CEE small‑multiples
- Extend lab scenarios/personas; add schema tests
- Mind oracle compilation path (mock → compiled)
- Additional sweep utilities and artifact summarizers

---

## Documentation

- Concept spec: CONCEPT.md
- Design and boundaries: src/crv/README.md
- Core contracts: src/crv/core/README.md
- Demo workflows: scripts/README.md

---

## Citation (Future-thinking)

If you use CRV‑ABM in academic work, please cite:

```
@misc{crv_abm,
  title        = {CRV-ABM: Context→Representation→Valuation Agent-Based Model},
  author       = {Dyckovsky, Ari M.},
  year         = {2025},
  howpublished = {\url{https://github.com/aridyckovsky/crv_agents}}
}
```

---

## License

MIT
