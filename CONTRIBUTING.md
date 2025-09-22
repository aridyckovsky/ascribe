# Contributing to crv_agents

Thanks for contributing! This document defines our contribution standards, with an emphasis on:

- Plan-anchor traceability to our source-of-truth plan(s)
- Google-style docstrings for Python APIs
- Small, well-scoped PRs with clear DoR/DoD checklists
- CI-green, docs-aligned changes

This is a docs/standards-only guide. For architectural scope and acceptance criteria, see:

- plans/crv_relother_rules_oracle_lab_audit_plan.md (source of truth for current phase)
- plans/crv_mvp_master_plan.md (longer horizon)
- prompts/\* (module-specific specifications and plans)

## Table of Contents

- Governance & Task Management
- Definition of Ready (DoR)
- Definition of Done (DoD)
- Issue & PR Hygiene
- Branch Strategy
- Labels & WIP Limits
- Docstring Standards (Google style)
- Acceptable Documentation Targets
- Test Standards
- Provenance & Schemas

---

## Governance & Task Management

All work must trace to a plan anchor. Scope is managed in plan files under `plans/`. Do not alter scope or acceptance in code or PR descriptions. Propose scope changes via a dedicated “Plan Change” PR that edits the relevant plan file(s) first.

- Source of Truth: `plans/crv_relother_rules_oracle_lab_audit_plan.md`
- Work breakdown: One GitHub issue per plan-implementation bullet and per testing group defined in the plan.
- Sprint Board: Backlog → Ready → In-Progress → PR → Review → Done

Commit to small, reviewable slices that keep the test suite green.

## Definition of Ready (DoR)

Before picking up an issue, ensure:

- Plan anchor is cited with a direct quote of the acceptance or behavior paragraph(s).
- Acceptance criteria are listed and test targets identified.
- Schema/data contracts (if any) are enumerated.
- Owner is assigned; estimation (Fibonacci) is provided.
- Cross-module impacts are noted (world ↔ mind ↔ lab ↔ viz).

## Definition of Done (DoD)

A PR is “Done” when:

- Code, docstrings, and docs/READMEs are updated to reflect the change.
- CI is green; tests cover acceptance criteria.
- Provenance and data contracts validated; schemas documented.
- PR links plan anchor(s) and includes test evidence (pytest summary, screenshots if UI).
- No stray TODO/FIXME remain; remaining work is explicitly tracked.

## Issue & PR Hygiene

- Issue Title: `[PLAN:<Section>] <Short task>`  
  Example: `[PLAN:Observation Rules] Implement GlobalVisibility + registry`
- Labels:
  - area(world|mind|lab|viz)
  - type(feature|test|docs|refactor)
  - priority(P1|P2|P3)
  - plan-anchor(<Section>)
- PR Title: Same format as Issue Title (link issue with “Closes #<id>”).
- PR Description:
  - Plan anchor quote(s) and link
  - Summary of changes and rationale
  - Schema changes (before/after if applicable)
  - Perf/latency notes (if relevant)
  - Test evidence (pytest summary, screenshots if applicable)

## Branch Strategy

- Branch types (examples):
  - `feature/plan-<anchor-slug>-<short-task>`
  - `docs/plan-<anchor-slug>-<short-task>`
  - `test/plan-<anchor-slug>-<short-task>`
- Keep branches focused and short-lived.

## Labels & WIP Limits

- WIP limits: In-Progress ≤ 4 total; PR ≤ 6 total (across the team).
- Always move work to Ready only when DoR is satisfied.

## Docstring Standards (Google style)

We use Google-style docstrings for all public Python APIs (modules, classes, functions/methods). Where math is required, include inline formulas that render well on GitHub (e.g., `V = v_base + φ·tanh(γ·U)`).

Example:

```python
def value_score(self) -> np.ndarray:
    """Compute bounded valuation per token.

    Uses formal readout: V = v_base + φ·tanh(γ·U) where
    U mixes identity, valence, direct triads, mediated other–other paths, and semantic spillover.

    Args:
        None

    Returns:
        np.ndarray: Valuation vector of shape (K,).

    Notes:
        - Boundedness: V in (-φ + v_base, +φ + v_base).
        - Parameters are configured in AgentParams (gamma_readout, phi_readout, alpha_oo, etc.).
    """
```

For classes and modules, include a high-level summary, parameter/attribute descriptions, invariants, and examples if applicable.

### Required Sections (as applicable)

- Summary: 1–2 lines describing the purpose and context.
- Args: Name, type, description, constraints.
- Returns/Yields: Type(s), shape(s), meaning.
- Raises: Error conditions with explanations.
- Notes: Invariants, provenance, performance considerations.
- Examples: Concise usage snippets relevant to the API.

## Acceptable Documentation Targets

- Markdown-only updates for READMEs and `AGENTS.md` across subpackages (world, mind, lab, viz, and root).
- No Sphinx/mkdocs scaffolding needed for now (unless explicitly requested).
- Keep examples executable or near-executable where practical.

## Test Standards

- Keep test suite green. Any change to schemas/exports should include a test to guard the contract.
- Prefer concise, focused tests with explicit checks on types/shapes and behavior.
- Use deterministic seeds or deterministic mock engines where relevant (e.g., mock oracle).

## Provenance & Schemas

- Events provenance fields:
  - `delay` (int|None)
  - `origin_rule` (str|None)
- Oracle calls:
  - Logged to `oracle_calls.parquet` with basic fields (tick, agent*id, render_hash, ctx*\*, value, source, cache_hit, latency_ms, t_enqueued).
- When you introduce or extend a schema, document the fields and types in module README or inline docstrings, and add tests to guard load/export behavior.

---

## Documentation (build & preview)

The canonical entrypoint for building docs (dev and CI) is the shell script:

```bash
# Build diagrams and site/ with strict checks
bash tools/generate_docs.sh
```

- This script:
  - Runs the Node-based grammar diagram build (`tools/ebnf`).
  - Invokes `uv run mkdocs build --strict` (which triggers `tools/build_docs.py` via mkdocs gen-files).
- Live preview (no diagrams step):
  ```bash
  uv run mkdocs serve
  ```

CI uses the same entrypoint in `.github/workflows/docs.yml` (“Build documentation” step).

### Using DSPy to author llms.txt (local & CI)

We use DSPy to synthesize `llms.txt` during MkDocs generation. A deterministic fallback is used only when DSPy isn’t configured (e.g., no key in forks/PRs).

Local (OpenAI provider)

```bash
# Enable DSPy authoring
export DOCS_USE_DSPY=true
export DOCS_DSPY_PROVIDER=openai
export DOCS_DSPY_MODEL=gpt-4o-mini
export OPENAI_API_KEY=sk-...            # Your OpenAI key

# Optional: canonical base URL used in seeds
export DOCS_BASE_URL=https://docs.ascribe.live

# Optional: reproducibility seed
export DOCS_DSPY_SEED=123

# Build docs (strict); llms.txt is generated virtually via mkdocs-gen-files
bash tools/generate_docs.sh

# Verify DSPy path was used (not the fallback):
head -n 1 site/llms.txt
# Should NOT equal: "# llms.txt (fallback)"
```

Future (OpenRouter provider; example only)

```bash
export DOCS_USE_DSPY=true
export DOCS_DSPY_PROVIDER=openrouter
export DOCS_DSPY_MODEL=openrouter/auto
export OPENROUTER_API_KEY=...           # Your OpenRouter key
export DOCS_BASE_URL=https://docs.ascribe.live
bash tools/generate_docs.sh
```

CI (GitHub Actions)

- The docs workflow `.github/workflows/docs.yml` is configured to:
  - Set job-level env for DSPy and the canonical base URL:
    - `DOCS_USE_DSPY=true`, `DOCS_DSPY_PROVIDER=openai`, `DOCS_DSPY_MODEL=gpt-4o-mini`, `DOCS_BASE_URL=https://docs.ascribe.live` (and optional `DOCS_DSPY_SEED`).
  - Pass `OPENAI_API_KEY` from repo secrets into the build step.
  - Assert that `llms.txt` was authored by DSPy (fails if the fallback appears) when the secret is available.
- Maintainers must add a repository secret:
  - Settings → Secrets and variables → Actions → New repository secret
  - Name: `OPENAI_API_KEY` (value: your key)
- Forks/PRs: secrets are not available; the assertion is skipped and the fallback output is acceptable in those runs.

Notes

- All generation uses mkdocs-gen-files (virtual docs). No repo-root writes occur.
- Switching providers later requires only environment changes; no code edits are necessary.
- The canonical base for live docs is https://docs.ascribe.live.

By following this guide, your contributions will integrate smoothly with our planning and review processes, remain traceable to plan anchors, and keep the repo consistent and maintainable. If you have questions about these guidelines, open a docs issue tagged `type(docs)` and `plan-anchor(<Section>)`.
