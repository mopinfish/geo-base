# geo-base API

The API service is a FastAPI server for vector, raster, and feature data.

## Development

```bash
uv sync --extra dev --frozen
uv run uvicorn lib.main:app --reload --port 8000
```

Run the formatting and lint checks with:

```bash
uv run ruff check .
uv run black --check .
```

Database-backed tests require `TEST_DATABASE_URL` pointing to a dedicated test database.
See the repository-level local development and testing manuals for the complete setup.
