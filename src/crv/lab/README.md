# CRV Lab

Experimental layer for CRV providing personas, scenarios, typed EDSL tasks, offline per‑persona policies, and probes/audits integrated with the Run Bundle. Lab artifacts are reproducible (Parquet + JSON manifests) and align with the Lab Restructure plan and CRV concept docs.

## At a Glance

- Personas: structured traits and loaders; easy AgentList construction.
- Scenarios: encoder with canonical ctx\_\* fields (file or synthetic).
- Typed tasks (EDSL): valuation baseline and scaffolds for other signatures.
- Offline policy: aggregate per‑persona policy.parquet from tidy results.
- Probes & audits: schedule tasks, compare against mind/oracle, write Run Bundle artifacts.

## Module Layout

- cli.py — thin CLI for building policies, showing heads, and pulling remote results
- policy_builder.py — end‑to‑end orchestration (mock/local/remote), manifests
- surveys.py — valuation question + Survey builder (EDSL); SURVEY_ID anchor
- scenarios.py — ScenarioSchema, loader (Parquet or synthetic), ScenarioList
- personas.py — Persona definitions, loaders, AgentList adapter
- modelspec.py — model registry, JSON loader, ModelList adapter
- policy.py — tidy normalization and per‑persona aggregation
- tasks.py — scaffolds for typed EDSL tasks (interpret/update/appraise/value_policy/produce_utterance)
- probes.py — schedule/run probes; tidy outputs to Run Bundle
- audit.py — compare mind/oracle outputs vs EDSL answers; audit artifacts
- io_helpers.py — writers for Run Bundle artifacts via crv.io

## Capabilities

- Build a valuation policy (mock/local/remote).
- Normalize EDSL results to a stable tidy schema.
- Aggregate tidy → policy with statistics (mean/sd/n).
- Emit manifests with seeds, versions, and paths.
- Schedule probes and write audits into a Run Bundle.

## Quickstart

1. Environment

- Python 3.13+
- Install uv:
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Or `pipx install uv`
- Optional keys:
  - Local EDSL: set `OPENAI_API_KEY` in `.env`
  - Remote EDSL: set `EXPECTED_PARROT_API_KEY` in `.env`

2. Install

```bash
uv sync
```

3. Mock policy (no keys)

```bash
uv run crv-lab build-policy --runs-root runs/demo --mode mock --persona persona_baseline --model gpt-4o
# Inspect outputs
ls runs/demo/<STAMP>/
uv run crv-lab show-policy --policy runs/demo/<STAMP>/policies/policy_crv_one_agent_valuation_v0.1.1.parquet
```

4. Local EDSL (requires OPENAI_API_KEY)

```bash
uv run crv-lab build-policy --runs-root runs/local --mode local --persona persona_baseline --model gpt-4o
```

5. Remote submission (Coop; EXPECTED_PARROT_API_KEY)

```bash
# Submit
uv run crv-lab build-policy --runs-root runs/remote --mode remote --persona persona_baseline --model gpt-4o
# Await completion inline
uv run crv-lab build-policy --runs-root runs/remote --mode remote --persona persona_baseline --model gpt-4o --await-remote
# Or pull later
uv run crv-lab pull-remote --runs-root runs/remote --stamp <STAMP>
```

## CLI Reference

Build a policy run:

```bash
uv run crv-lab build-policy \
  --runs-root RUNS_ROOT \
  --mode {mock|local|remote} \
  [--persona P] [--personas-file FILE] \
  [--model M] [--models-file FILE] \
  [--scenarios PATH] [--seed N] [--iterations N] \
  [--stamp STAMP] [--await-remote] \
  [--poll-interval SEC] [--timeout SEC] [--no-env] [--print-manifest]
```

Show a policy head:

```bash
uv run crv-lab show-policy --policy path/to/policy.parquet [--n ROWS]
```

Pull remote results (materialize tidy/policy):

```bash
uv run crv-lab pull-remote --runs-root RUNS_ROOT --stamp STAMP [--job UUID] [--poll-interval SEC] [--timeout SEC] [--no-env] [--print-manifest]
```

## Modes & Credentials

- `--mode mock`: deterministic seeded answers (no keys).
- `--mode local`: EDSL execution; requires `OPENAI_API_KEY` for GPT slugs.
- `--mode remote`: submits to Expected Parrot Coop; requires `EXPECTED_PARROT_API_KEY`.
  - On submission: writes a manifest with `remote_job`; tidy/policy are created after completion (await inline or `pull-remote` later).

## Scenarios (scenarios.py)

- Required base fields: `ctx_*` → `ctx_token_kind`, `ctx_owner_status`, `ctx_peer_alignment`.
- Derived when missing: `ctx_salient_other_alignment`, `ctx_recent_affect`, `ctx_group_label`.
- Loader behavior:
  - If `--scenarios` points to a Parquet file with required fields, it is used.
  - Otherwise, a small synthetic grid is synthesized for demos.
- ScenarioList emitted via:

```python
from edsl import ScenarioList
ScenarioList.from_list("ctx", rows)
```

## Personas & Models

- personas.py:
  - `DEFAULT_PERSONAS` includes `persona_baseline` (simple identity/affect placeholders).
  - `load_personas_file(Path)` loads JSON list or dict.
  - `build_agent_list(personas)` → EDSL AgentList.
- modelspec.py:
  - `DEFAULT_MODELS` (example: map `gpt-4o` → coop slug `gpt-4o-mini`).
  - `load_models_file(Path)` loads JSON.
  - `build_model_list(specs, use_coop_slug=bool)` → EDSL ModelList.
  - CLI auto‑selects defaults when files not provided.

## Survey & Valuation (surveys.py)

- SURVEY_ID: `crv_one_agent_valuation_v0.1.1`
- `build_question()`: QuestionLinearScale (1–7) with explicit `ctx_*` variables:
  - group label, salient other alignment, recent affect, ownership, peer alignment.
- `build_survey()`: wraps the question in an EDSL Survey.

## Normalization & Aggregation

- `policy.tidy_results(raw_df)`:
  - Ensures stable schema: `ctx_*`, `persona`, `model`, `question`, `answer (int64)`, `prompt_hash`, `source`.
  - Deterministic ordering for downstream consumers.
- `policy.aggregate_policy(tidy_df)`:
  - Group by `ctx_*` + `persona` + `model` and compute `value_mean`, `value_sd`, `n`.
- Wrappers exposed in `policy_builder` for compatibility (`tidy_results`, `aggregate_policy`).

## Manifests (policy_builder.write_manifest)

Manifest JSON records:

- `timestamp`, `survey_id`, `run_stamp`, `runs_root`.
- `git_commit` (if available), `edsl_version` (if available).
- `meta`:
  - `mode`, `seed`, `personas`, `models`.
  - `persona_traits`, `models_meta`.
  - `scenarios_source` (file path or `"synthetic:default"`).
  - `iterations` (remote).
  - `openai_key_present`, `expected_parrot_key_present`.
  - row counts and paths: `raw_path`, `tidy_path`, `policy_path`.
  - `prompt_hashes` (unique count).
  - `remote_job` details and `remote_completed` (for remote).
  - `error` (when failures occur).

## Probes & Audits (Run Bundle IO)

- `probes.schedule_probes(states_df, cfg)` → time-based manifest.
- `probes.run_probes(cfg, manifest_df)` → tidy-style outputs (scaffold tasks).
- `audit.compare(settings, run_id, survey_id?)` → MAE summary when tidy has both `answer` and `value`.
- Writers (io_helpers.py) place artifacts under:

```
<root>/runs/<run_id>/artifacts/lab/{tidy,probes,policy,audit}/…
```

## Data Contracts

- `tidy_<survey_id>.parquet` columns:
  - `ctx_*` (string), `persona` (string), `model` (string), `question` (string),
  - `answer` (int64; 1–7), `prompt_hash` (string), `source` (string).
- `policy_<survey_id>.parquet` columns:
  - `ctx_*` (string), `persona` (string), `model` (string),
  - `value_mean` (float64), `value_sd` (float64), `n` (int64).

## Troubleshooting

- Missing `ctx_*` in tidy:
  - `policy_builder` attempts to normalize typical shapes (e.g., `scenario.*`, `scenario.ctx.*`) and align to the expected grid.
- Remote UUID missing:
  - `pull-remote` requires a job UUID (via manifest or `--job`).
- Keys:
  - Local runs with GPT slugs need `OPENAI_API_KEY`; remote runs require `EXPECTED_PARROT_API_KEY`.
- Strictness:
  - Normalization fixes types/ordering; downstream tests expect consistent schema.

## Testing

```bash
uv run ruff check .
uv run mypy --strict
uv run pytest -q
```

## Contributing

- Follow `prompts/LAB_RESTRUCTURE_PLAN.md` and concept docs.
- Keep typed outputs stable; prefer Polars (avoid pandas in library code).

## References

- Concept docs: `concept_docs/architecture_concept.md`, `concept_docs/crv_architecture_alignment.md`, `concept_docs/crv_math_alignment_notes.md`, `concept_docs/messy_math_spec.tex`, `concept_docs/react_mem0_gepa_overview.md`
- Plans: `prompts/LAB_RESTRUCTURE_PLAN.md`, `plans/crv_mvp_master_plan.md`, `plans/crv_relother_rules_oracle_lab_audit_plan.md`, `plans/crv_relother_rules_oracle_lab_audit_plan_addendum_2025-09-19.md`
