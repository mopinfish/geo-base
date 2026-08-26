# Testing

```bash
cd api && uv run ruff check . && uv run black --check .
cd mcp && uv run ruff check . && uv run pytest -q
cd app && npm run lint && npx tsc --noEmit && npm test
```

API database tests require `TEST_DATABASE_URL` whose database name is `geo_base_test`. Do not substitute a development database.
