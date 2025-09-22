# `crv/` — Core namespaces for the Context–Representation–Valuation stack

> **Status:** Design document. This README describes the intended layout and contracts for the `crv/` root package before implementation.

The `crv` package is a **vendor‑neutral**, cohesive namespace for the project’s cognitive modeling stack. It organizes code by **role** rather than by library:

- `crv.world` — world simulation (Mesa)
- `crv.lab` — empirical elicitation & policy building (EDSL)
- `crv.mind` — cognitive micro‑functions & oracle (DSPy)
- `crv.viz` — visualization (Altair)
- `crv.io` — canonical IO layer (Polars/Arrow-first, append‑only, per‑table manifests)

This structure improves readability, testing, and long‑term maintainability while staying faithful to the CRV model (Context → Representation → Valuation).

---

## Package structure

```
crv/
  world/                 # ABM world & agents (Mesa)
    __init__.py          # public API: Model, Agent, run_sim, SimConfig
    agents.py            # agent classes (TokenAgent, etc.)
    model.py             # CRV state, representation store, step logic
    events.py            # context events & generators
    sim.py               # simulation loop, CLI entry points
    sweep.py             # parameter sweeps / experiments
    metrics.py           # DataCollector helpers & reporters
    data_io.py           # read/write Parquet/CSV for runs; no vendor deps

  lab/                   # EDSL‑driven elicitation & policies
    __init__.py          # public API: build_policy, run_survey, …
    surveys.py           # question templates; valuation survey builder
    scenarios.py         # context encoders → ScenarioList
    personas.py          # persona specs (traits)
    modelspec.py         # model slugs / routing config (names only)
    run.py               # `.by(...).run()` orchestration → tidy tables
    policy.py            # tidy → policy.parquet aggregation
    audit.py             # targeted audits vs. predictions

  mind/                  # DSPy cognitive modules & oracle
    __init__.py          # public API: compile_value_token, OracleBatcher
    signatures.py        # typed Signatures (Attend, Appraise, ValueToken…)
    programs.py          # assembled DSPy Modules
    compile.py           # optimizers & metrics → compiled programs
    oracle.py            # batched, t+1 barrier oracle; engine‑agnostic
    cache.py             # local cache (e.g., sqlite/duckdb) & hashing
    eval.py              # MAE/calibration/ablations

  viz/                   # Visualization (Altair)
    __init__.py          # public API: charts
    charts.py            # single charts (pure functions)
    dashboards.py        # composed multi‑view dashboards
    themes.py            # styles and shared encodings
```

## IO layer (crv.io)

- Canonical, append‑only IO with tick‑bucket partitioning and per‑table manifests.
- Polars/Arrow‑first; atomic tmp→ready renames; strict validation vs `crv.core.tables`.
- See `src/crv/io/README.md` for usage and API (`IoSettings`, `Dataset`).

---

## Integrated system

### Offline path (fast, sweep‑friendly for ABMs)

```
lab.surveys/run  →  tidy results  →  lab.policy (aggregate)  →  policy.parquet  →  world.sim (lookup)
```

- Build a structured valuation survey; run over scenario × persona × model.
- Normalize to tidy tables; aggregate to `policy.parquet` with means/SD/N.
- `world` agents read valuations via O(1) lookups; perfect for parameter sweeps.

### Online oracle (adaptive, deterministic)

```
world.sim (tick t)  →  mind.oracle.batch (dedupe + cache)  →  compiled modules  →  answers applied at tick t+1
```

- Batch all agent queries per tick; deduplicate; respect a local cache.
- Answers are **applied next tick** (barrier semantics) for determinism.
- Graceful fallback to offline `policy.parquet` if the oracle abstains or times out.

### Audit loop (ground truth checks)

```
world.sim (sampled states)  →  lab.run (EDSL)  →  compare vs. mind & policy  →  write audit artifacts
```

- Periodically elicit labels on visited states; log divergences for calibration and re‑compilation.

---

## Dependency boundaries

- `crv.world` **must not import** from `crv.lab` or `crv.mind`. It talks to them only via **data contracts** (files) or **engine interfaces** passed at runtime.
- `crv.lab` has no runtime dependency on `crv.world` or `crv.mind`. It outputs tidy tables and policies.
- `crv.mind` depends on **data schemas** from `crv.lab` (not code) and exposes engine‑agnostic oracles.
- `crv.viz` reads artifacts; it **does not mutate** state or write core data.

This boundary keeps vendor libraries (Mesa, EDSL, DSPy, Altair) **encapsulated** and replaceable.

---

## Data contracts (requires stable schemas)

### Policy Parquet (from `crv.lab.policy`)

- `ctx_token_kind: str`
- `ctx_owner_status: str`
- `ctx_peer_alignment: str`
- `persona: str`
- `model: str`
- `value_mean: float64`
- `value_sd: float64`
- `n: int64`

### Oracle calls (from `crv.mind.oracle`)

- `tick: int64`
- `agent_id: str|int`
- `ctx_token_kind, ctx_owner_status, ctx_peer_alignment`
- `persona, model`
- `value: int64` (0–7; 0 = abstain)
- `source: str` (`cache|compiled|fallback|mock`)
- `cache_hit: bool`
- `latency_ms: int64`
- `render_hash: str`

### Run manifests (provenance)

- EDSL: `survey_id`, model slugs, parameters, cache stats, datetime, prompt hashes count, git SHA.
- DSPy: signature versions, optimizer, metric curves, datetime, git SHA.
- Sim: seeds, config, steps, oracle settings, datetime, git SHA.

> **Rule:** Changing question wording, scenario schema, or signature I/O **requires** a version bump (`survey_id` or `signature_id`) and manifests must reflect it.

---

## Public API (anticipated)

```python
# crv.world
from crv.world.sim import run_sim, SimConfig
from crv.world.model import Model

# crv.lab
from crv.lab.policy import build_policy, write_policy
from crv.lab.surveys import build_valuation_survey

# crv.mind
from crv.mind.compile import compile_value_token
from crv.mind.oracle import OracleBatcher

# crv.viz
from crv.viz.charts import valuation_histogram
```

These re‑exports keep user imports concise while hiding internal file layout.

---

## Conventions & style

- **Naming**: packages/modules = `lower_snake_case`; classes = `PascalCase`; functions/vars = `lower_snake_case`.
- **No vendor names** or `ai_*` prefixes in packages/modules. Use role names (`world`, `lab`, `mind`, `viz`).
- **No** `utils.py`/`helpers.py`. Prefer specific modules (`policy.py`, `oracle.py`, `metrics.py`).
- **Typing**: full type hints; `from __future__ import annotations`.
- **Docstrings**: Google‑style with `Args/Returns/Raises` and one short example.
- **Logging**: INFO by default; log paths, row counts, cache stats.
- **Determinism**: seed Mesa RNG; barrier semantics for oracle; snapshot rendered prompts where applicable.

---

## Testing (minimum bar)

- **Schema tests**: required columns/types for policy and oracle outputs.
- **Determinism tests**: identical inputs → identical `prompt_hash`/`render_hash` and cached answers.
- **Barrier test**: valuations from tick _t_ are applied at _t+1_.
- **Ablations**: attention/memory toggles change valuations in expected directions.

Test files by role: `tests/test_world_*.py`, `tests/test_lab_*.py`, `tests/test_mind_*.py`, `tests/test_viz_*.py`.

---

## CLI entry points (future)

- `crv-lab` — run surveys, build policies, run audits.
- `crv-world` — run simulations and sweeps.
- `crv-mind` — compile programs, run oracles.
- `crv-viz` — export charts/dashboards from artifacts.

(These are thin wrappers around the Python APIs; optional for now.)

---

## Migration notes

- Introduce `crv/` alongside existing modules.
- Add temporary shims (`crv_abm` → `crv.world`, `edsl` → `crv.lab`) to maintain compatibility while refactoring.
- Update imports incrementally; remove shims in a major version bump.

---

## Roadmap (initial milestones)

1. Scaffold `crv/` with empty modules and docstrings; wire public API in `__init__.py` files.
2. Move or wrap current Mesa code into `crv.world` without behavior changes.
3. Implement `crv.lab.policy` (offline path) using existing EDSL scripts.
4. Add `crv.mind.oracle` (mock first), then compiled program support.
5. Begin audits and evaluation harness.

---

## Run Bundle quickstart (world.sim)

By default, world.sim saves outputs under out/runs/<run_id> (or a project-wide root configured via IoSettings). The run-bundle manifest is always written to bundle.manifest.json.

Examples:

- python -m crv.world.sim --steps 1 --run-id demo
- python -m crv.world.sim --steps 1 --run-id demo --root-dir /tmp/crv_out

Outputs (baseline):

- <root>/runs/<run_id>/agents_tokens.parquet
- <root>/runs/<run_id>/model.parquet
- <root>/runs/<run_id>/metadata.json
- <root>/runs/<run_id>/bundle.manifest.json

Notes:

- When --out is omitted, world.sim defaults to out_dir = <root_dir>/runs/<run_id>.
- --root-dir overrides repository defaults from TOML/env.

## IO configuration (project-wide)

IoSettings.load() resolves config with precedence:

- Environment variables (prefix CRV*IO*)
- TOML (./crv.toml or pyproject.toml [tool.crv.io])
- Built-in defaults

TOML (crv.toml):
[io]
root_dir = "out"
tick_bucket_size = 100
compression = "zstd"
strict_schema = true

Environment:
export CRV_IO_ROOT_DIR="out"
export CRV_IO_TICK_BUCKET_SIZE="100"
export CRV_IO_COMPRESSION="zstd"
export CRV_IO_STRICT_SCHEMA="1"

Details and full examples live in src/crv/io/README.md.

## Orchestration: lab → audit → bundle

A convenience script generates lab artifacts and an audit summary into the Run Bundle, then refreshes bundle.manifest.json:

- python scripts/lab_probe_and_audit.py --run-id lab_demo
- python scripts/lab_probe_and_audit.py --run-id lab_demo --root-dir /tmp/crv_out --rows 8

Writes under <root>/runs/<run_id>/artifacts/lab/:

- tidy/tidy.parquet (or tidy\_{survey_id}.parquet)
- audit/audit_summary.parquet
- audit/audit_summary.json

Then updates bundle.manifest.json so downstream tools can discover tables and artifacts without scanning Parquet.

_This README is the source of truth for the `crv/` package layout and contracts until code lands. Keep it updated as interfaces stabilize._
