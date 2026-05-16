# geo-base Deployment Guide

> English: this page ・ 日本語: [DEPLOY.ja.md](./DEPLOY.ja.md)

> [!NOTE]
> This document is a **high-level summary of the deployment flow**. For per-component details, see the linked guides below.
>
> The legacy Vercel API deployment flow (Vercel + Supabase) was retired by 2026-05-10.

## Current Architecture

| Component | Platform | URL | Deployment guide |
|---|---|---|---|
| API (FastAPI) | Fly.io | `geo-base-api.fly.dev` | [`api/FLY_DEPLOY.md`](./api/FLY_DEPLOY.md) (Japanese) |
| MCP Server | Fly.io | `geo-base-mcp.fly.dev` | `cd mcp && fly deploy` |
| Admin UI (Next.js) | Vercel | `geo-base-admin.vercel.app` | GitHub push triggers auto-deploy |
| PostgreSQL + PostGIS | Fly.io (`geo-base-pg`) | internal: `geo-base-pg.internal` | [`docs/POSTGRES_SETUP.md`](./docs/POSTGRES_SETUP.md) |
| Redis | Upstash (cache) | — | `REDIS_URL` env var |
| Storage (COG/PMTiles) | Fly Tigris (S3-compatible) | — | Planned in Issue #72 Phase 1.2 |

## Branches and Automation

- `develop`: active development branch; PRs target `develop`
- `main`: stable release branch; Vercel Production tracks `main`
- API/MCP production deploys are manual via `fly deploy`
- Admin UI production deploys are automatic on push to `main`

## Authentication

- Only `AUTH_PROVIDER=local` is supported. See [`docs/AUTH_SETUP.md`](./docs/AUTH_SETUP.md).
- Create the initial admin user with:

```bash
flyctl ssh console -a geo-base-api -C 'python -m lib.auth.cli create-admin --email <email>'
```

## Troubleshooting

If you run into DB connectivity or API startup issues, check the relevant component guides:

- API: [`api/FLY_DEPLOY.md`](./api/FLY_DEPLOY.md) (Japanese)
- DB: [`docs/POSTGRES_SETUP.md`](./docs/POSTGRES_SETUP.md)
- Auth: [`docs/AUTH_SETUP.md`](./docs/AUTH_SETUP.md)

## Related Docs

- Architecture decision log: [`docs/INFRA_MIGRATION_INVESTIGATION.md`](./docs/INFRA_MIGRATION_INVESTIGATION.md) (Japanese / internal)
- Authorization review: [`docs/ACCESS_CONTROL_REVIEW.md`](./docs/ACCESS_CONTROL_REVIEW.md)
- Local development: [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md)
