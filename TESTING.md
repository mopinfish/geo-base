# geo-base Verification Guide

> English: this page ・ 日本語: [TESTING.ja.md](./TESTING.ja.md)

This guide summarizes how to verify geo-base locally and against production.

## Unit Tests

### API

The API tests require a dedicated test database (`geo_base_test`).

```fish
cd docker
docker compose up -d
cd ..

cd api
uv sync --extra dev
set -x TEST_DATABASE_URL postgresql://postgres:postgres@localhost:5432/geo_base_test
uv run pytest tests/ -q
```

### MCP

```fish
cd mcp
uv sync --extra dev
uv run pytest -v
uv run pytest tests/test_tools.py -v
uv run pytest tests/test_geocoding.py -v
uv run pytest tests/test_crud.py -v
```

## Local Verification

### API

```fish
cd api
uv sync
uv run uvicorn lib.main:app --reload --port 8000
curl http://localhost:8000/api/health
curl http://localhost:8000/api/tilesets
curl "http://localhost:8000/api/features?bbox=139.5,35.5,140.0,36.0&limit=5"
```

### MCP live test

```fish
cd mcp
TILE_SERVER_URL=http://localhost:3000 uv run python tests/live_test.py
```

### Claude Desktop

- Configure the MCP server in Claude Desktop using the local `uv` path
- Verify tileset listing and geocoding prompts

## Production Verification

### API

```fish
curl https://geo-base-api.fly.dev/api/health
curl https://geo-base-api.fly.dev/api/health/db
curl https://geo-base-api.fly.dev/api/tilesets
```

### MCP

```fish
curl -N https://geo-base-mcp.fly.dev/sse
cd mcp
TILE_SERVER_URL=https://geo-base-api.fly.dev uv run python tests/live_test.py
```

### CRUD checks

- Log in and fetch a JWT token
- Create, update, and delete a tileset
- Create, update, and delete a feature

## Troubleshooting

- `Connection refused`: the server is not running
- `401 Unauthorized`: missing or invalid token
- `403 Forbidden`: insufficient permissions
- `500 Internal Server Error`: inspect the service logs

For the detailed Japanese walkthrough, open `TESTING.ja.md`.
