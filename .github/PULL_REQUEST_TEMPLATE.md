## Summary

<!--
1-3 sentences describing what this PR changes and why.
Focus on the *why* — the diff already shows the what.
-->

## Linked issue

<!-- Use "Closes #N" to auto-close on merge, or "Refs: #N" for context. -->

Closes #

## Type of change

<!-- Check all that apply. -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would change existing behavior)
- [ ] Documentation only
- [ ] Refactoring / dead code removal
- [ ] Test-only change
- [ ] CI / infra change

## How was this tested?

<!--
Describe the verification steps. Examples:
- `cd api && uv run pytest tests/ -q` → all green
- `cd app && npm test` → 56 passed
- Manual: navigated to /tilesets/new, created a PMTiles tileset, confirmed the redirect to /tilesets/<id>
- `npm run test:e2e:smoke` → 10 passed
-->

## Checklist

- [ ] PR title follows the commit convention (e.g. `feat(app): ...`, `fix(api): ...`)
- [ ] Lints and tests pass locally
- [ ] New behavior is covered by tests where reasonable
- [ ] Public-facing strings (API errors, UI copy, docs) follow the project's [i18n strategy](./docs/superpowers/specs/2026-05-10-i18n-strategy-design.md) (English for public surfaces; UI strings via catalogs once Phase 3 lands)
- [ ] If introducing migrations, added a new numbered file under `docker/postgis-init/` rather than editing an existing one
- [ ] For Admin UI changes: no hardcoded user-facing strings outside the catalog (once `next-intl` is in place)

## Additional notes

<!-- Anything reviewers should know: trade-offs you made, follow-up work, screenshots, etc. -->
