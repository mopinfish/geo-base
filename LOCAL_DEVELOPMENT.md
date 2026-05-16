# geo-base Local Development

> English: this page ・ 日本語: [LOCAL_DEVELOPMENT.ja.md](./LOCAL_DEVELOPMENT.ja.md)

This guide explains how to run each geo-base component locally.

> For authentication details (`AUTH_PROVIDER=local`, initial admin creation, and troubleshooting),
> see [`docs/AUTH_SETUP.md`](docs/AUTH_SETUP.md).

## Port Mapping

| Component | Port | Directory | Description |
|---|---|---|---|
| Admin UI | 3000 | `/app` | Next.js admin console |
| API | 8000 | `/api` | FastAPI tile server |
| MCP Server | stdio | `/mcp` | Claude Desktop integration (default: stdio; SSE: `MCP_TRANSPORT=sse MCP_PORT=8001`) |

## Prerequisites

- Node.js 18+
- Python 3.11+
- `uv` (Python package manager)
- PostgreSQL + PostGIS (`docker compose up -d postgis`, under `docker/`)

## Startup

### Start all components (3 terminals)

```fish
# Terminal 1: API (FastAPI)
cd api
uv run uvicorn lib.main:app --reload --port 8000

# Terminal 2: MCP Server (optional)
cd mcp
set -x TILE_SERVER_URL http://localhost:8000
uv run python server.py

# Terminal 3: Admin UI (Next.js)
cd app
npm run dev
```

### Start only the Admin UI (using the production API)

```fish
cd app

# Configure .env.local for the production API
echo 'NEXT_PUBLIC_API_URL=https://geo-base-api.fly.dev' > .env.local

npm run dev
```

### Start only the API

```fish
cd api
uv run uvicorn lib.main:app --reload --port 8000
```

## Environment Variables

### API (`/api/.env`)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base

# Auth provider (`local` only; Supabase support was removed in Issue #72)
AUTH_PROVIDER=local

# JWT settings (required in local mode; generate with `openssl rand -base64 64`)
JWT_SECRET=your-jwt-secret
JWT_AUDIENCE=authenticated
JWT_ISSUER=geo-base
ACCESS_TOKEN_TTL_SECONDS=900

# Email (invitations and password reset)
EMAIL_BACKEND=console            # null / console / smtp
INVITATION_BASE_URL=http://localhost:3000

# CORS / Cookie
CORS_ORIGINS=http://localhost:3000
COOKIE_SAMESITE=lax
COOKIE_SECURE=false

# Local-provider specific
LOCAL_AUTH_ALLOW_SIGNUP=false    # set to true only if public signup is allowed
```

For the full variable reference, see [`docs/AUTH_SETUP.md`](docs/AUTH_SETUP.md).

### MCP Server (`/mcp/.env`)

```env
TILE_SERVER_URL=http://localhost:8000
DEBUG=true
API_TOKEN=your-api-token
```

### Admin UI (`/app/.env.local`)

```env
# Local development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MCP_URL=http://localhost:8001

# Production API
# NEXT_PUBLIC_API_URL=https://geo-base-api.fly.dev
# NEXT_PUBLIC_MCP_URL=https://geo-base-mcp.fly.dev
```

## Verification

### API health check

```fish
# Local
curl http://localhost:8000/api/health

# Production
curl https://geo-base-api.fly.dev/api/health
```

### Tileset list

```fish
curl http://localhost:8000/api/tilesets
```

### Admin UI

Open http://localhost:3000 in your browser.

## Troubleshooting

### Port already in use

```fish
lsof -i :3000
lsof -i :8000
lsof -i :8001

# Then stop the process
kill -9 <PID>
```

### CORS errors

When the API is running locally, CORS is allowed automatically.
If you are using the production API, set `.env.local` to the production URL.

### Database connection errors

```fish
# Confirm PostgreSQL is running
pg_isready -h localhost -p 5432

# If Docker Compose is not already running
cd docker && docker compose up -d postgis
```

---

# Vercel Deployment Layout (Admin UI Only)

> Vercel deploys only the **Admin UI (Next.js) `geo-base-admin` project**.
> The FastAPI tile server now runs on Fly.io (`geo-base-api`).
> The legacy Vercel API deployment (`geo-base`) was retired; see `api/FLY_DEPLOY.md`.

## Reference Project Layout

| Project | Platform | Root Directory | URL | Deployment guide |
|---|---|---|---|---|
| `geo-base-admin` | **Vercel** | `app` | https://geo-base-admin.vercel.app | This section |
| `geo-base-api` | Fly.io | `api` | https://geo-base-api.fly.dev | `api/FLY_DEPLOY.md` |
| `geo-base-mcp` | Fly.io | `mcp` | https://geo-base-mcp.fly.dev | `cd mcp && fly deploy` |
| `geo-base-pg` | Fly.io | `pg` | `geo-base-pg.internal` (internal) | `docs/POSTGRES_SETUP.md` |

## Create the Vercel project

### 1. Create a project in Vercel Dashboard

1. Log in to the [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New...** → **Project**
3. Select the same repository: `mopinfish/geo-base`
4. Click **Import**

### 2. Project settings

| Setting | Value |
|---|---|
| Project Name | `geo-base-admin` |
| Framework Preset | `Next.js` (auto-detected) |
| Root Directory | `app` |
| Build Command | default |
| Output Directory | default |

### 3. Environment variables

| Variable | Value | Notes |
|---|---|---|
| `API_BACKEND_URL` | `https://geo-base-api.fly.dev` | Required in Production; target of the `/api/*` rewrite in `next.config.ts` |
| `NEXT_PUBLIC_API_URL` | empty | Use same-origin fetch in production |
| `NEXT_PUBLIC_MCP_URL` | `https://geo-base-mcp.fly.dev` | Production MCP URL |

### 4. Deploy

Click **Deploy**.

### 5. Verify

- Admin UI: `https://geo-base-admin.vercel.app`
- API health: `https://geo-base-api.fly.dev/api/health`

---

## Production URLs

| Service | URL | Platform |
|---|---|---|
| Admin UI | https://geo-base-admin.vercel.app | Vercel |
| API | https://geo-base-api.fly.dev | Fly.io |
| MCP Server | https://geo-base-mcp.fly.dev | Fly.io |
| PostgreSQL + PostGIS | `geo-base-pg.internal` (Fly internal network) | Fly.io (`geo-base-pg`) |
