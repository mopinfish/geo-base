# Contributing

Open an Issue before large changes. Keep Pull Requests focused, use English identifiers and comments, and add regression tests for bug fixes.

Run the relevant checks before submitting:

```bash
cd api && uv run ruff check . && uv run black --check .
cd mcp && uv run ruff check . && uv run pytest -q
cd app && npm run lint && npx tsc --noEmit && npm test
```

Database tests require `TEST_DATABASE_URL` pointing to a dedicated `geo_base_test` database. Never run them against development or production data.
