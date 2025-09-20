# CRV Core

Foundational library providing formal domain specification language and typings.

## Schema Versioning

- The canonical schema descriptor lives in `crv.core.versioning.SchemaVersion` and is exported as `SCHEMA_V`. This metadata drives JSON schema generation, Parquet table guards, and CLI compatibility checks.
- Compatibility helpers (`is_compatible`) validate both the major and minor components against `SCHEMA_V`, ensuring downstream tools only operate on known-good artifacts.
- Use `is_successor_of` when proposing a new schema release to ensure version bumps follow the sequential minor/major progression enforced across the monorepo.
- When bumping the schema, update `SCHEMA_V` directly, regenerate dependent schemas, and ship new tests/doc updates in the same change. Runtime overrides are intentionally unsupported to preserve reproducibility.
