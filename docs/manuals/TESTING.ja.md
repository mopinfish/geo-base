# テスト

```bash
cd api && uv run ruff check . && uv run black --check .
cd mcp && uv run ruff check . && uv run pytest -q
cd app && npm run lint && npx tsc --noEmit && npm test
```

APIのDBテストには、DB名が`geo_base_test`である`TEST_DATABASE_URL`が必要です。開発DBを代用しないでください。
