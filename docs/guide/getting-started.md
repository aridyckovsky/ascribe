# Getting Started

Follow these steps to set up Ascribe with CIRVA models locally and run a minimal example.

## Prerequisites

- Python 3.13+ (verify: `python3 --version`)
- uv (Python packaging tool)

Install uv (macOS/Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pipx:

```bash
pipx install uv
```

## Clone and install

```bash
git clone https://github.com/aridyckovsky/ascribe.git
cd ascribe
uv sync
```

## Quick start

Run a small demo (see `scripts/` for more examples):

```bash
uv run python scripts/run_small_sim.py
```

## Develop/docs locally

Build docs (strict):

```bash
bash tools/generate_docs.sh
open site/index.html
```

## Next steps

### Read the Core contracts and grammar

- [Core](../api/crv/core/index.md)
- [Grammar (EBNF)](../grammar/ebnf.md)
- [Grammar Diagrams](../grammar/diagrams.html)

### Explore module guides

- [IO](../api/crv/io/index.md)
- [Lab](../api/crv/lab/index.md)
- [Mind](../api/crv/mind/index.md)
- [World](../api/crv/world/index.md)
- [Viz](../api/crv/viz/index.md)

## Key Dependencies

- [Polars](https://pola.rs)
- [Expected Parrot EDSL](https://docs.expectedparrot.com/)
- [DSPy](https://dspy.ai)
- [Mesa](https://mesa.readthedocs.io)
- [Vega-Altair](https://altair-viz.github.io/)
