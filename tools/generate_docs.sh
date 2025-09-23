#!/usr/bin/env bash
# Canonical docs build entrypoint for dev and CI.
# - Grammar EBNF markdown is generated via tools/build_docs.py (mkdocs gen-files) at build time.
# - Ensures Node deps are available; diagrams are generated during mkdocs gen-files. Runs strict mkdocs build.
set -euo pipefail

# Ensure Node deps for diagrams CLI (ebnf2railroad) are installed; actual generation happens in mkdocs gen-files
# Prefer deterministic install when a lockfile exists; otherwise fallback to install
if [ -f tools/ebnf/package-lock.json ]; then
  npm --prefix tools/ebnf ci
else
  npm --prefix tools/ebnf install --no-audit --no-fund
fi

# Sync Python dependencies (docs group includes local 'tools' via uv workspace)
uv sync --extra docs

# Ensure Python can import the repo-root 'tools' package during mkdocs gen-files
export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"

# Silence litellm DeprecationWarning about missing event loop during DSPy calls
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore:There is no current event loop:DeprecationWarning}"

# Enforce DSPy generation when OpenAI key is present (fail fast if DSPy unavailable)
if [ -n "${OPENAI_API_KEY:-}" ]; then
  export DOCS_DSPY_REQUIRED="${DOCS_DSPY_REQUIRED:-true}"
fi

# Mark that we're using the canonical wrapper (guard enforced in tools/build_docs.py)
export ASCRIBE_DOCS_VIA_WRAPPER=1

# Build or serve docs (default: build). Pass through extra args.
cmd="${1:-build}"
if [ $# -gt 0 ]; then
  shift
fi

case "$cmd" in
  build)
    # Strict MkDocs build (gen-files runs tools/build_docs.py during build)
    uv run mkdocs build --strict "$@"
    ;;
  serve)
    # Local dev server with correct PYTHONPATH and guard
    uv run mkdocs serve "$@"
    ;;
  *)
    echo "Usage: $0 [build|serve] [-- mkdocs args]" >&2
    exit 2
    ;;
esac
