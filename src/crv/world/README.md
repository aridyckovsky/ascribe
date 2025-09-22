# CRV World

The World module defines the simulation environment: agents, events, configuration, and runtime model orchestration.

What it provides

- Agent model and roster management
- Event envelopes and scheduling
- World configuration and model wiring
- Observation rules and visibility policies
- Simulation loop utilities

Quick start

- Install dependencies with uv (or pip):
  ```bash
  uv sync
  ```
- Minimal usage (Python):

  ```python
  # Example imports from the world module
  from crv.world.model import CRVModel
  from crv.world.config import WorldConfig
  from crv.world.agents import CRVAgent

  # Construct a small model (illustrative)
  cfg = WorldConfig()
  agents = [CRVAgent(index=i) for i in range(3)]
  model = CRVModel(config=cfg, agents=agents)

  # Step the model (see API Reference for details)
  # model.step()
  ```

Next steps

- See API Reference for detailed types and APIs:
  - crv.world (package index)
  - Submodules (agents, config, data, events, model, observation_rules, sim, sweep)
- Review the Guide’s Getting Started for setup and workflow context.
