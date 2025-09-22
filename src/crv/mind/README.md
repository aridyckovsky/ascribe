# CRV Mind

The Mind module hosts reasoning/oracle components and program interfaces used by agents and pipelines.

What it provides

- Oracle interfaces and types for model-backed reasoning
- Program compilation/execution helpers
- Controller utilities for ReAct-style flows
- Common signatures and data types shared across mind components

Quick start

- Install dependencies with uv (or pip):
  ```bash
  uv sync
  ```
- Minimal usage (Python):

  ```python
  # Example: import mind components
  from crv.mind.oracle import Oracle  # concrete oracle(s)
  from crv.mind.signatures import Thought, Action  # shared types

  # Stub construction for demonstration; see API Reference for details
  # oracle = Oracle.from_config(...)
  # result = oracle.ask("What should the agent do next?")
  # print(result)
  ```

Next steps

- Read the API Reference for module details:
  - crv.mind (package index)
  - Submodules (oracle, oracle_types, programs, react_controller, signatures)
- Explore the Guide’s Getting Started for setup and workflow context.
