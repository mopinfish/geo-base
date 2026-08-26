# geo-base

> English | [日本語](./README.ja.md)

geo-base is a self-hostable open-source geospatial platform for small teams. It combines a FastAPI tile API, a Next.js administration interface, PostGIS-backed vector data, raster/vector tile delivery, and an MCP server for AI clients.

## FOSS4G 2026 Hiroshima

The presentation *A Self-Hostable Open-Source Geospatial Platform for Small Teams, with Natural Language Querying via MCP* and its reproducible demo are available in [docs/foss4g-2026](./docs/foss4g-2026/README.md).

## Components

- `api/`: FastAPI raster and vector tile API
- `app/`: Next.js administration UI
- `mcp/`: FastMCP tools for geospatial operations
- `docker/`: local PostGIS and Redis services

## Local setup

Requirements: Python 3.11+, Node.js 20+, Docker, Docker Compose, and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mopinfish/geo-base.git
cd geo-base
docker compose -f docker/docker-compose.yml up -d
```

Then start the services in separate terminals:

```bash
cd api && uv sync && uv run uvicorn lib.main:app --reload --port 8000
cd mcp && uv sync && uv run python server.py
cd app && npm install && npm run dev
```

Copy each service's `.env.example` to its documented runtime file before use. See [local development](./docs/manuals/LOCAL_DEVELOPMENT.md), [deployment](./docs/manuals/DEPLOY.md), and [testing](./docs/manuals/TESTING.md).

## Supported data

Vector paths include GeoJSON, MVT, MBTiles, and PMTiles. Raster paths include GeoTIFF/COG, PNG, and JPEG. Support varies by import and serving path; consult the service documentation before production use.

## Contributing and security

Contributions are welcome through Issues and Pull Requests. Read [CONTRIBUTING.md](./CONTRIBUTING.md). Report vulnerabilities according to [SECURITY.md](./SECURITY.md).

## License

MIT — see [LICENSE](./LICENSE).
