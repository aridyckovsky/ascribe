#!/usr/bin/env bash
# TODO: This naming is off, need to consider difference wiht build_docs.py
set -euo pipefail

uv run python tools/generate_ebnf_md.py
if [ -d tools/ebnf/node_modules ]; then
  npm --prefix tools/ebnf run diagrams
else
  npm --prefix tools/ebnf ci
  npm --prefix tools/ebnf run diagrams
fi

uv run mkdocs build --strict
