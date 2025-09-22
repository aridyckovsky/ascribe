#!/usr/bin/env bash
# Canonical docs build entrypoint for dev and CI.
# - Grammar EBNF markdown is generated via tools/build_docs.py (mkdocs gen-files) at build time.
# - Ensures Node deps are available; diagrams are generated during mkdocs gen-files. Runs strict mkdocs build.
set -euo pipefail

# Ensure Node deps for diagrams CLI (ebnf2railroad) are installed; actual generation happens in mkdocs gen-files
if [ -d tools/ebnf/node_modules ]; then
  npm --prefix tools/ebnf ci
else
  npm --prefix tools/ebnf ci
fi

# Strict MkDocs build (gen-files runs tools/build_docs.py during build)
uv run mkdocs build --strict
