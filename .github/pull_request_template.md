<!--
Title format: <area>: <concise feature>
Examples:
- core: introduce canonical grammar, schemas, and versioning
- app: add initial Streamlit run visualization
- io: canonical IO layer (append-only) + manifests

Use this template for feature PRs. Prefer concise, technical language.
For drafts, append " (WIP)" to the title.
-->

## Summary

<!-- 2–5 sentences. What is changing and why it matters to users/developers? Keep it crisp. -->

## Motivation

<!-- Problem statement or gap. Why now? Link to plan/ADR/spec where relevant. -->

## Scope of Changes (by file)

<!-- List key files and the nature of change. Keep one bullet per path when possible. -->

- path/to/file.py (new): brief description
- path/to/other_file.py (modified): brief description
- tests/... (added/updated): coverage note

## Approach

<!-- Architectural approach and key decisions. Alternatives considered if relevant. -->

## User Impact

<!-- UX/API behavior changes. Feature flags, defaults, deprecations. -->

## API / DB Changes

<!-- New/changed public APIs, schemas, migrations. Note compatibility guarantees. -->

## Backward Compatibility / Migration

<!-- Breaking changes and required migration steps. Provide example/playbook if needed. -->

## Performance

<!-- Baseline vs after (numbers if applicable) or N/A with rationale. -->

## Security / Privacy

<!-- Data handling, permissions, threat considerations, secrets, PII. -->

## Testing Plan

<!-- What is tested and how (unit/integration/e2e). Edge cases. How reviewers can verify locally. -->

## Rollout / Ops

<!-- Feature flags, staged rollout, monitoring/alerts, rollback plan. -->

## Docs / Changelog

<!-- Docs updated (docs/...), mkdocs nav, API docs, and release notes entry. -->

## Screenshots / Recordings (optional)

<!-- Paste images or links to short gifs/videos for UX changes. -->

## Risks and Mitigations

<!-- Top 3–5 risks and how they’re mitigated or monitored. -->

## References

<!-- Linked issues/PRs/specs/ADRs. Use close syntax for issues. -->

- Closes #<issue-id>
- ADR/Plan: plans/audited/...

## Checklist

- [ ] Scope is clear; non-goals noted
- [ ] Linked issues and references added (Closes #… / ADRs / specs)
- [ ] Breaking changes called out with migration guidance (if any)
- [ ] API/DB changes documented; migrations included
- [ ] Tests added/updated; coverage for critical paths
- [ ] Performance considered (numbers or N/A + rationale)
- [ ] Security/Privacy considerations addressed
- [ ] Feature flags and rollback plan (or N/A)
- [ ] Docs updated (docs/…, mkdocs nav) and release notes prepared
- [ ] CI green: lint/type/test
