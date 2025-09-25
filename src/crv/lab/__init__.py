"""
crv.lab — Policy building, tasks, probes, and audit (IO‑first helpers).

## Responsibilities
- Build and manage persona policies for offline/remote elicitation and fast sweeps.
- Define tasks and probes for controlled scenario generation and auditing.
- Produce tidy artifacts and (optionally) index decisions/policy into canonical IO tables (crv.io).
- Remain read‑write at the artifact layer, but avoid duplicating world logic.

## Public API
- io_helpers — IO‑first helpers for writing/reading lab artifacts.
- policy_builder — Persona policy authoring/elicitation (remote/local).
- tasks — Orchestration for scenario bundles and runner glue.
- probes — Probes and audits that summarize runs.
- audit — Higher‑level audit/report writers.

## Import DAG discipline
- Depends on: stdlib, crv.core, crv.io (Dataset), optionally pydantic/polars.
- Must not import crv.world runtime; any world reading should use IO via crv.io selectors.
- Must not import crv.viz dashboards (viz remains read‑only and can use lab outputs).

## Examples
```python
# Write a tidy artifact for a lab sweep (IO-first)  # doctest: +SKIP
from crv.lab.io_helpers import write_tidy_artifact  # doctest: +SKIP
from crv.io import IoSettings, Dataset  # doctest: +SKIP
settings = IoSettings(root_dir="runs/out")  # doctest: +SKIP
ds = Dataset(settings, run_id="demo_abcdef")  # doctest: +SKIP
write_tidy_artifact(ds, payload={"persona": "baseline", "result": "ok"})  # doctest: +SKIP
```

## References
- [audit](audit.md)
- [cli](cli.md)
- [io_helpers](io_helpers.md)
- [modelspec](modelspec.md)
- [personas](personas.md)
- [policy_builder](policy_builder.md)
- [policy](policy.md)
- [probes](probes.md)
- [scenarios](scenarios.md)
- [survey](survey.md)
- [surveys](surveys.md)
- [tasks](tasks.md)
"""
