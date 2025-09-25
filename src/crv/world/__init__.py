"""
crv.world — Deterministic ABM world, agents, events, and visibility/observation rules.

## Responsibilities
- Execute the barriered CRV loop (Context → Representation → Valuation → Action) deterministically.
- Manage agents, events, and observation/visibility rules (delays, channels, topology).
- Integrate IO-first writing via crv.io (append-only parquet + per-table manifests).
- Preserve reproducibility (seeded RNGs, run manifests, provenance).

## Public API
- model — World model and step loop mechanics.
- agents — Agent scaffolding and state.
- observation_rules — Visibility/delivery policies (global, group, delayed, topology).
- sim — Entry points for running simulations and small demos.
- sweep — Simple sweep harnesses (parameter scans) when applicable.

## Import DAG discipline
- Depends on: stdlib, crv.core (contracts), crv.io (IO-first writers), mesa (runtime), and local modules.
- Must not import crv.lab or crv.mind at runtime. Interactions happen via data contracts (files) or injected interfaces.
- crv.viz reads artifacts only and must not be imported here.

## Examples
```python
# Minimal sketch (API varies by version)  # doctest: +SKIP
from crv.world.model import CRVModel
from crv.io import IoSettings
from crv.core.ids import RunId

settings = IoSettings.load()
m = CRVModel(io_settings=settings, run_id=RunId("demo_abcdef"))
m.step()  # advance one tick
```

## References
- [agents](agents.md)
- [config](config.md)
- [data](data.md)
- [events](events.md)
- [mesa_data](mesa_data.md)
- [model](model.md)
- [observation_rules](observation_rules.md)
- [sim](sim.md)
- [sweep](sweep.md)
"""
