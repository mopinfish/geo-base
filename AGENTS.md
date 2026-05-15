# Repository Guidelines

## Project Structure & Module Organization

This repository is a monorepo with three main services:

- `api/`: FastAPI tile server. Application code lives in `api/lib/`; tests live in `api/tests/`.
- `app/`: Next.js 16 admin UI. Routes are under `app/src/app/`, shared UI in `app/src/components/`, and browser/e2e tests in `app/tests/e2e/`.
- `mcp/`: FastMCP server. Tool implementations are in `mcp/tools/`; tests are in `mcp/tests/`.

Supporting files live in `docker/` for local PostGIS/Redis setup, `scripts/` for utility scripts, and `docs/` for design, auth, and operations notes.

## Build, Test, and Development Commands

Run services from their own directories:

- `cd api && uv sync && uv run uvicorn lib.main:app --reload --port 8000`: start the API locally.
- `cd app && npm install && npm run dev`: start the admin UI on port `3000`.
- `cd mcp && uv sync && uv run python server.py`: start the MCP server.
- `docker compose -f docker/docker-compose.yml up -d`: start local PostGIS and Redis.

Quality checks:

- `cd api && uv run ruff check . && uv run black --check .`
- `cd app && npm run lint && npx tsc --noEmit && npm test`
- `cd mcp && uv run ruff check . && uv run pytest -q`

## Coding Style & Naming Conventions

Python uses `ruff` and `black` with a `100`-character line limit and `py311` target. TypeScript follows the existing Next.js + ESLint setup. Use English for identifiers, files, comments, and new docstrings. Follow existing naming patterns: `test_*.py` for Python tests, `*.spec.ts` for Playwright, and lowercase kebab-case for UI component filenames such as `delete-tileset-dialog.tsx`.

## Testing Guidelines

Use `pytest` in `api/` and `mcp/`, `vitest` for frontend unit tests, and Playwright for end-to-end coverage. API tests that touch the database require `TEST_DATABASE_URL` pointing to the dedicated `geo_base_test` database; do not run them against the development DB. Add a regression test for every bug fix and cover at least one edge case for new features.

## Commit & Pull Request Guidelines

Recent history follows relaxed Conventional Commits, for example `fix(datasources): ...` and `feat(app/i18n): ...`. Preferred branch prefixes are `feat/...`, `fix/...`, and `docs/...`. Keep PRs focused, link issues in the body (`Closes #123`), run the relevant checks before pushing, and include screenshots for UI changes.
