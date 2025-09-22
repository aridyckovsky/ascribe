#!/usr/bin/env bash
# Canonical docs build entrypoint for dev and CI.
# - Grammar EBNF markdown is generated via tools/build_docs.py (mkdocs gen-files) at build time.
# - This script handles Node-based diagram generation and runs the strict mkdocs build.
set -euo pipefail

# Build EBNF diagrams (Node step)
if [ -d tools/ebnf/node_modules ]; then
  npm --prefix tools/ebnf run diagrams
else
  npm --prefix tools/ebnf ci
  npm --prefix tools/ebnf run diagrams
fi

# Strict MkDocs build (gen-files runs tools/build_docs.py during build)
uv run mkdocs build --strict
