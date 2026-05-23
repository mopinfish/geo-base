# geo-base

> 🌐 **English**: this page ・ **日本語**: [README.ja.md](./README.ja.md)

A monorepo geospatial tile server system.

## Overview

`geo-base` is a tile server system that serves geospatial data (raster and vector tiles).

### Key components

1. **Tile server (`api/`)** — REST API that serves raster and vector tiles dynamically from PostGIS or pre-built archives (PMTiles, COG).
2. **MCP server (`mcp/`)** — Model Context Protocol server that exposes the project's geospatial tools to AI clients such as Claude Desktop.
3. **Admin UI (`app/`)** — Web console for uploading, managing, and previewing tilesets.

## Tech stack

### Backend

- **Tile server**: Python FastAPI (deployed to Fly.io as `geo-base-api`)
- **MCP server**: Python FastMCP (Fly.io / runnable locally)
- **Database**: PostgreSQL + PostGIS (Fly.io app `geo-base-pg`)
- **Storage**: Fly Tigris (S3-compatible). Direct uploads are persisted as internal `s3://bucket/path` URLs in a private bucket.
- **Cache**: Redis (Upstash). Health endpoint: `GET /api/health/redis`.

### Frontend

- **Admin UI**: Next.js 16 (App Router) + React 19 + TypeScript + Tailwind v4 + shadcn/ui, deployed to Vercel
- **Map library**: MapLibre GL JS
- **Authentication**: Self-hosted local provider (JWT + bcrypt, `AUTH_PROVIDER=local`)

## Repository layout

```
geo-base/
├── api/                 # FastAPI tile server
├── app/                 # Next.js admin UI
├── mcp/                 # MCP server
├── docker/              # Local-development Docker stack (PostGIS + Redis)
├── scripts/             # Utility scripts (seeding, fixtures, etc.)
└── packages/            # Shared packages
```

## Documentation

- Deployment guide: [DEPLOY.md](./DEPLOY.md)
- Local development: [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)
- Auth setup: [docs/AUTH_SETUP.md](./docs/AUTH_SETUP.md)
- PostgreSQL setup: [docs/POSTGRES_SETUP.md](./docs/POSTGRES_SETUP.md)
- Redis setup: [docs/REDIS_SETUP.md](./docs/REDIS_SETUP.md)
- Access control review: [docs/ACCESS_CONTROL_REVIEW.md](./docs/ACCESS_CONTROL_REVIEW.md)
- Verification guide: [TESTING.md](./TESTING.md)

## Local ports

| Service | Port | Start command |
|---|---|---|
| Admin UI (Next.js) | **3000** | `cd app && npm run dev` |
| API (FastAPI) | **8000** | `cd api && uv run uvicorn lib.main:app --reload --port 8000` |
| MCP Server | **8001** | `cd mcp && TILE_SERVER_URL=http://localhost:8000 uv run python server.py` |
| PostGIS | 5432 | `cd docker && docker compose up -d` |
| Redis | 6379 | (same compose file) |

> **Note:** Some older docs show API on port 3000. The correct convention is **API=8000, Admin UI=3000**.

## Local development setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- [`uv`](https://docs.astral.sh/uv/) — Python package manager

### Installing `uv`

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# or via pip
pip install uv
```

### Bring up the stack

```bash
# Clone the repository
git clone https://github.com/mopinfish/geo-base.git
cd geo-base

# Start PostGIS + Redis locally
cd docker
docker compose up -d
cd ..

# Tile server (FastAPI) — runs on :8000
cd api
uv sync
uv run uvicorn lib.main:app --reload --port 8000
cd ..

# MCP server — stdio mode by default
cd mcp
uv sync
uv run python server.py
cd ..

# Admin UI (Next.js) — runs on :3000
cd app
npm install
npm run dev
cd ..
```

### Environment variables

The three service directories (`api/`, `app/`, `mcp/`) each ship an `.env.example`. Copy it to the file the runtime expects and fill in the values that fit your environment:

- `api/` and `mcp/` (Python): copy `.env.example` to `.env`
- `app/` (Next.js): copy `.env.example` to `.env.local`. Next.js does load plain `.env`, but this repository's convention is to use `.env.local` for the Admin UI so local-only secrets stay out of git (`.env.local` is gitignored by default in Next.js scaffolds).

## Supported formats

### Raster tiles

- GeoTIFF / Cloud Optimized GeoTIFF (COG)
- PNG (including data-PNG such as elevation tiles)
- JPG

### Vector tiles

- GeoJSON
- Mapbox Vector Tile (MVT / `.pbf`)
- MBTiles
- PMTiles

## Contributing

We welcome contributions. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening a pull request. For security issues, see [SECURITY.md](./SECURITY.md).

## License

MIT License — see [LICENSE](./LICENSE).
