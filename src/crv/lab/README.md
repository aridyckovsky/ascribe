# crv.lab — EDSL policy building for CRV

Purpose

- crv.lab encapsulates Expected Parrot EDSL usage to elicit structured judgments and aggregate them into a policy table consumed by the CRV simulator.
- Outputs include a tidy policy Parquet and a manifest with provenance for replayability and audits.

Module layout

- cli.py — command-line entry points (build-policy, show-policy)
- policy_builder.py — run orchestration, normalization, aggregation, and stamped artifact writing
- survey.py — EDSL survey pieces (question, scenarios, agents, models)
- AGENTS.md — detailed standards and practices for EDSL in this repo

Requirements

- Python 3.13 (project-level setting)
- uv (>= 0.8) for environment and scripts
- OPENAI_API_KEY in .env for local runs (Remote Inference is optional)
- python-dotenv is used to load .env automatically by default

Quick start (mock or local runs)

1. Install and sync:
   - uv venv
   - source .venv/bin/activate # Windows: .venv\Scripts\activate
   - uv sync
2. (Optional) Configure keys in `.env`:
   - OPENAI_API_KEY=sk-... # required for `--mode local`
   - EXPECTED_PARROT_API_KEY=ep-... # required for `--mode remote`
3. Build a mock policy run (no API keys needed):
   - uv run crv-lab build-policy --runs-root runs/demo --mode mock --persona persona_baseline --model gpt-4o
   - Artifacts land under `runs/demo/<STAMP>/` with `raw/`, `tidy/`, `policies/`, and `manifest_*`.
4. Inspect outputs:
   - ls runs/demo/<STAMP>/policies/
   - uv run crv-lab show-policy --policy runs/demo/<STAMP>/policies/policy_crv_one_agent_valuation_v0.1.0.parquet

Remote inference

- Requires an Expected Parrot Coop account and credits.
- Ensure `EXPECTED_PARROT_API_KEY` is present in `.env` and run:
  - uv run crv-lab build-policy --runs-root runs/remote --mode remote --persona persona_baseline --model gpt-4o
- The CLI submits a remote job and records its UUID in the manifest. No policy parquet is written until the job completes; track status in Coop or poll the API before re-running aggregation. Once the job reports `completed` (and the remote cache contains answers), either re-run `crv-lab build-policy --mode local --await-remote ...` to wait for completion inline or call `uv run crv-lab pull-remote --runs-root RUNS_ROOT --stamp STAMP` to download results and materialize the policy in-place.
- If submission fails (validation error, auth, etc.), the CLI exits non-zero and still writes a manifest capturing the error message for audit. Coop response details (for example, validation fields) are stored under `meta.remote_job` when available.
- The CLI aborts on validation errors; check the Coop jobs dashboard for details if the run fails.

CLI reference

- Build a policy run:
  ```
  uv run crv-lab build-policy --runs-root RUNS_ROOT --mode {mock|local|remote} [--persona P] [--personas-file FILE] [--model M] [--models-file FILE] [--scenarios PATH] [--seed N] [--iterations N] [--stamp STAMP] [--await-remote] [--poll-interval SEC] [--timeout SEC] [--no-env]
  ```
- Show a policy:
  ```
  uv run crv-lab show-policy --policy path/to/policy.parquet [--n ROWS]
  ```
- Pull remote results:
  ```
  uv run crv-lab pull-remote --runs-root RUNS_ROOT --stamp STAMP [--job UUID] [--poll-interval SEC] [--timeout SEC]
  ```
- Key flags:
  - `--runs-root`: root directory for stamped runs (default `runs`).
  - `--mode`: `mock` (deterministic hash answers), `local` (Expected Parrot via local provider SDKs), or `remote` (Expected Parrot Coop jobs).
  - `--scenarios`: Parquet with required `ctx_*` columns; omit to use the synthetic demo grid.
  - `--seed`: controls mock hash determinism and manifest provenance.
  - `--personas-file`: JSON file describing persona traits (used unless overridden by `--persona`).
  - `--models-file`: JSON file defining model specs (slug, coop slug, provider, notes).
  - `--iterations`: number of iterations for Coop remote jobs (default `1`).
  - `--await-remote`: block until the Coop job completes and pull results immediately.
  - `--poll-interval` / `--timeout`: polling cadence and timeout when awaiting completion.
  - `--no-env`: skip loading `.env` before resolving credentials.
  - `--print-manifest`: echo the manifest path on completion.
  - Remote mode writes only a submission manifest until results are downloaded. Use `--await-remote` or `crv-lab pull-remote` to materialize tidy/policy files once the job finishes.

Survey components

- Question (`surveys.py`): Linear 1–7 Likert with ctx variables (`ctx_token_kind`, `ctx_owner_status`, `ctx_peer_alignment`, plus social/affect cues).
- Scenarios (`scenarios.py`): ScenarioList built from Polars frames with extended context columns (`ctx_*`). Optional JSON overrides can enrich defaults.
- Personas (`personas.py`): Structured persona definitions with traits/notes, serialized into manifests.
- Models (`modelspec.py`): Coop-compatible model slug mapping, provider metadata, and notes.

Outputs and data contracts

- Run directory layout: `RUNS_ROOT/<STAMP>/`
  - `raw/raw_<survey_id>.parquet`
  - `tidy/tidy_<survey_id>.parquet`
  - `policies/policy_<survey_id>.parquet`
  - `manifest_<survey_id>.json`
- Tidy table schema extends the AGENTS contract with `prompt_hash` and additional context fields (`ctx_salient_other_alignment`, `ctx_recent_affect`, `ctx_group_label`).
- Policy schema:
  - ctx_token_kind, ctx_owner_status, ctx_peer_alignment, ctx_salient_other_alignment, ctx_recent_affect, ctx_group_label, persona, model, value_mean, value_sd, n
- Manifest JSON captures:
  - `timestamp`, `survey_id`, `run_stamp`, `runs_root`, git commit, edsl version
  - Execution metadata (`mode`, seeds, persona/model lists, persona trait summaries, model metadata, iterations, scenario source, prompt hash count, key presence, raw/tidy/policy paths, optional EDSL job ids)
  - Remote submissions additionally record the remote job payload and UUID; tidy/policy paths are omitted until aggregation is rerun.

Troubleshooting

- “QuestionScenarioRenderError: variables still present”:
  - Ensure the question template uses ctx.\* variables (e.g., ctx.ctx_token_kind).
  - Ensure scenarios are constructed with ScenarioList.from_list("ctx", ...).
- “EDSL results missing ctx columns”:
  - The build now tries to extract ctx\__ from typical shapes (scenario._, scenario.ctx.\*, top-level ctx struct).
  - If ctx\_\* columns still don’t appear but row count matches the expected grid, positional alignment is applied to produce a valid tidy table.
- “Validation Error” on remote runs:
  - This often indicates a routing/registry issue or a provider-side constraint; check the Coop Jobs page for the full validator error.
  - For development, prefer `--mode local` with `OPENAI_API_KEY` set in `.env`.
- No keys found:
  - The CLI auto-loads `.env`; pass `--no-env` to disable. Ensure `.env` contains `OPENAI_API_KEY` for local runs and `EXPECTED_PARROT_API_KEY` for remote runs.

Contributing

- Keep survey.py conservative and readable:
  - Canonical variable names and ctx namespace.
  - Avoid provider-specific switches and keep model slugs simple.
- Bump SURVEY_ID if changing question wording or scenario schema.
- Add/extend tests in tests/ to cover normalization, schema, and determinism.
- Run the standard checks before pushing:
  - uv run ruff
  - uv run mypy --strict
  - uv run pytest -q
- No pandas in library code; use Polars for data frames and Arrow via to_pandas() only at EDSL boundaries.
- Keep outputs deterministic and reproducible; manifests must include seeds and versions.

Examples

- Deterministic mock run:
  - uv run crv-lab build-policy --runs-root runs/demo --mode mock --persona persona_baseline --model gpt-4o
- Local EDSL execution (requires OPENAI_API_KEY):
  - uv run crv-lab build-policy --runs-root runs/local --mode local --persona persona_baseline --model gpt-4o
- Remote submission (await completion):
  - uv run crv-lab build-policy --runs-root runs/remote --mode remote --persona persona_baseline --model gpt-4o --await-remote
- Remote submission (deferred pull):
  - uv run crv-lab build-policy --runs-root runs/remote --mode remote --persona persona_baseline --model gpt-4o
  - uv run crv-lab pull-remote --runs-root runs/remote --stamp <STAMP>
- Custom scenario grid:
  - uv run crv-lab build-policy --runs-root runs/scenarios --mode mock --scenarios data/my_scenarios.parquet
- EDSL docs (Surveys, Scenarios, Agents, Models, Results)
- Inspect output:
  - uv run crv-lab show-policy --policy runs/demo/<STAMP>/policies/policy_crv_one_agent_valuation_v0.1.0.parquet

Run Bundle integration and audit

- Lab helpers write artifacts to <root>/runs/<run_id>/artifacts/lab/{tidy,probes,policy,audit}/
- Examples:
  - python scripts/lab_probe_and_audit.py --run-id lab_demo
  - python scripts/lab_probe_and_audit.py --run-id lab_demo --root-dir /tmp/crv_out --rows 8
- The script resolves IoSettings.load() precedence (env > TOML > defaults) and refreshes bundle.manifest.json for discoverability.

References

- EDSL docs (Surveys, Scenarios, Agents, Models, Results)

- EDSL docs (Surveys, Scenarios, Agents, Models, Results)
- Expected Parrot Remote Inference docs (setup, jobs, credits)
- AGENTS.md in this directory for our internal style and contracts

Notes

- This module intentionally favors a minimal, robust local flow (gpt-4o + OPENAI_API_KEY) and adds only the normalization needed to stabilize outputs across EDSL versions and backends. Remote inference is optional and can be enabled later without changing your local workflow.
