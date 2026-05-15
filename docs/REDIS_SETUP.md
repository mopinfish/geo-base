# Redis Cache Setup Guide

> English: this page ・ 日本語: [REDIS_SETUP.ja.md](./REDIS_SETUP.ja.md)

geo-base API uses Redis to cache tile data, TileJSON, and tileset metadata.
If Redis is unavailable, the service falls back to in-memory cache behavior.

## Cached Data

| Data | Key pattern | Default TTL |
|---|---|---|
| Vector tiles | `tile:vector:{id}:{z}:{x}:{y}` | 3600s |
| Raster tiles | `tile:raster:{id}:{z}:{x}:{y}` | 3600s |
| PMTiles tiles | `tile:pmtiles:{id}:{z}:{x}:{y}` | 3600s |
| TileJSON | `tilejson:{type}:{id}` | 300s |
| Tileset info | `tileset:{id}` | 60s |

## Local Development

1. Start PostgreSQL and Redis:

```fish
cd docker
docker compose up -d
```

2. Set environment variables:

```env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_KEY_PREFIX=geo-base:
TILE_CACHE_TTL=3600
TILEJSON_CACHE_TTL=300
TILESET_INFO_CACHE_TTL=60
```

3. Start the API:

```fish
cd api
uv sync
uv run uvicorn main:app --reload
```

4. Verify:

```fish
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/db
curl http://localhost:8000/api/health/cache
```

## Fly.io / Production

- Set `REDIS_URL` in the API app secrets
- Confirm the Redis host is reachable from the API
- Deploy with `fly deploy`

## Notes

- Avoid `KEYS` in production; use `SCAN` instead
- Use `REDIS_KEY_PREFIX` to keep keys scoped to geo-base
- Check `/api/health/redis` when troubleshooting cache health
