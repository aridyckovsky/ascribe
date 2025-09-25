"""
crv.mind — Deterministic oracle batching, signatures, and ReAct controller (IO logging).

## Responsibilities
- Provide deterministic oracle batching with cache for reproducible cognition traces.
- Define persona/signature scaffolding and a simple ReAct-style controller.
- Log LLM/tool calls to canonical IO (oracle_calls) with timing and cache provenance.

## Public API
- OracleBatcher — Batched requests with sqlite cache and deterministic behavior.
- signatures — Signature descriptors/types for prompts and tools.
- react_controller — Step‑level coordination of tool use with guardrails.
- tools — Optional adapters (e.g., mem0 client) and read helpers (world_read).

## Import DAG discipline
- Depends on: stdlib, crv.core, optionally pydantic/sqlite3; crv.io when IO logging is enabled.
- Must not import crv.world runtime; read helpers operate via crv.io only.
- External services (LLMs, memory) must be optional and guarded.

## Examples
```python
# Log oracle calls to IO (oracle_calls table)  # doctest: +SKIP
from crv.mind.oracle import OracleBatcher
from crv.io import IoSettings, Dataset
batcher = OracleBatcher(io_settings=IoSettings(root_dir="runs/out"),
                        run_id="demo_abcdef")  # doctest: +SKIP
_ = batcher.ask(engine="gpt-4o", signature_id="sign_v1", value={"q": "hello"})  # doctest: +SKIP
batcher.flush()  # writes to TableName.ORACLE_CALLS via Dataset  # doctest: +SKIP
```

## References
- [cache](cache.md)
- [compile](compile.md)
- [eval](eval.md)
- [oracle_types](oracle_types.md)
- [oracle](oracle.md)
- [programs](programs.md)
- [react_controller](react_controller.md)
- [signatures](signatures.md)
"""
