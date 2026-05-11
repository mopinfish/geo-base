# Contributing to geo-base

Thanks for taking the time to contribute. This document describes how to propose changes, the conventions we follow, and how translations are handled.

If you read Japanese and prefer it for context, the project's internal handover and roadmap files (`HANDOVER_*.md`, `ROADMAP_*.md`, `CLAUDE.md`) remain in Japanese and provide more historical detail.

## Code of conduct

Be respectful in issues, pull requests, and discussions. Disagreements about technical direction are welcome; personal attacks are not.

## Ways to contribute

- **Bug reports** — open an issue using the *Bug report* template.
- **Feature proposals** — open an issue using the *Feature request* template. Larger proposals benefit from a short design discussion before implementation.
- **Pull requests** — see "Submitting a pull request" below.
- **Translations** — see "Translations" below.
- **Documentation** — fixes to README, `docs/`, or inline documentation are always welcome.

## Local development

See the "Local development setup" section of [README.md](./README.md). In short:

```bash
docker compose -f docker/docker-compose.yml up -d
# api/   → uv sync && uv run uvicorn lib.main:app --reload --port 8000
# app/   → npm install && npm run dev    (port 3000)
# mcp/   → uv sync && uv run python server.py
```

Useful checks before opening a pull request:

```bash
cd api && uv run ruff check . && uv run black --check . && uv run pytest tests/ -q
cd app && npm run lint && npx tsc --noEmit && npm test
cd mcp && uv run ruff check . && uv run pytest -q
```

For end-to-end Playwright tests, see [`app/tests/e2e/README.md`](./app/tests/e2e/README.md).

## Submitting a pull request

1. **Fork or branch** — for outside contributors, fork the repository; maintainers use feature branches in this repo (`feat/...`, `fix/...`, `docs/...`).
2. **Keep PRs focused** — one logical change per PR. Bundle related refactors only when they directly support the change.
3. **Write tests** — bug fixes need a regression test; new features need coverage for the happy path and at least one edge case. Use `tests/e2e/regression/` for cross-cutting regression scenarios.
4. **Run the checks above** before pushing. CI will run the same lints and tests.
5. **Reference issues** — link the issue your PR closes (`Closes #123`) or refers to (`Refs: #123`) in the body, not the title.
6. **Mark `draft`** if your PR is still in progress, then flip to *ready for review* once CI is green.

### Commit messages

We follow a relaxed Conventional Commits style:

```
<type>(<scope>): <short summary>

<body — wrap at ~72 chars, explain *why*, not just what>

Refs: #<issue-number>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`. Common scopes: `api`, `app`, `mcp`, `e2e`, `auth`, `infra`. Summaries can be in English or Japanese — both are accepted for now.

Prefer small, frequent commits over single squashed bombs. When CI hooks fail, fix the cause and create a new commit rather than amending a published one.

### Pull request reviews

- **AI reviews**: CodeRabbit and GitHub Copilot may add review comments. Address them inline; if a suggestion is out of scope, reply with the reason rather than silently dismissing.
- **Human reviews**: maintainers review structural changes (new endpoints, schema changes, deployment-affecting work). Smaller doc and copy fixes can be merged after CI is green.

### Code style

- **Python** (`api/`, `mcp/`): `ruff` + `black`, line length **100**, target `py311`. `uv` only — no direct `pip`.
- **TypeScript** (`app/`): ESLint + Prettier defaults from the framework. Use existing `shadcn/ui` primitives before introducing new ones.
- **SQL migrations** (`docker/postgis-init/`): numbered files (`NN_*.sql`). Production schema is rebuilt from this directory; never edit a file that has already shipped — add a new numbered migration instead.

### Code comments and identifiers

- **New code**: comments and docstrings should be written in **English**.
- **Existing code**: do not bulk-translate existing Japanese comments. When you touch a function, you may translate the comments inside it — but a PR whose only purpose is comment translation is unlikely to be merged unless coordinated with the maintainers.
- **Identifiers** (function, variable, type, file names): always English. This has been the convention from the start of the project.
- **User-facing strings in the Admin UI** are handled by the `next-intl` message catalogs (see "Translations" below) once Phase 3 of the i18n initiative lands. Until then, new UI strings can be Japanese.

## Translations

geo-base is built primarily in Japanese but is moving toward English-first public surfaces (README, API errors, MCP descriptions, public docs) and a bilingual Admin UI. The strategy is documented in [`docs/superpowers/specs/2026-05-10-i18n-strategy-design.md`](./docs/superpowers/specs/2026-05-10-i18n-strategy-design.md).

### What is in scope

- **Public surfaces** are English-first: README, CONTRIBUTING, SECURITY, issue/PR templates, API error messages, OpenAPI descriptions, MCP tool descriptions, and public documentation under `docs/`.
- **Admin UI** is being internationalized with [`next-intl`](https://next-intl-docs.vercel.app/) (JA + EN initially, extensible). Catalog location: `app/src/locales/<locale>/<namespace>.json` once introduced.

### What is out of scope

- Internal handover and roadmap documents (`HANDOVER_*.md`, `ROADMAP_*.md`, `CLAUDE.md`, `docs/AUTH_E2E_CHECKLIST.md`, `docs/INFRA_MIGRATION_INVESTIGATION.md`, etc.) remain in Japanese.
- DB content (tileset names, descriptions written by users) is not translated.
- Log and trace output is not internationalized.

### Workflow

1. **Drafting** — AI translation (Claude or similar) for first drafts is encouraged. Keep terminology consistent: `tileset`, `datasource`, `feature`, `layer`, `MVT`, `PMTiles` are translation-stable terms.
2. **Review** — at least one maintainer reviews the translated copy before merge. Reviewers should check tone (we aim for neutral and concise) and accuracy.
3. **Parity** — when adding a translated file, keep both languages in lock-step: if you update `README.md`, update `README.ja.md` in the same PR. The CI for the Admin UI also enforces that `en` and `ja` message catalogs have identical key sets.

### Adding a new language

Once Phase 3 (Admin UI i18n) lands, additional locales can be added by:

1. Creating `app/src/locales/<locale>/` with the same namespace files as `en/`.
2. Adding the locale to the list in `app/i18n.ts` (or equivalent config).
3. Opening a PR with a brief note explaining the target audience.

We accept community-contributed locales subject to maintainer review. Outside `app/`, only `en` and `ja` are maintained.

## Security

Please do not report security vulnerabilities in public issues. See [SECURITY.md](./SECURITY.md) for the private disclosure process.

## License

By contributing, you agree that your contributions are licensed under the MIT License (see [LICENSE](./LICENSE)).
