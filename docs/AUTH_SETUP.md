# Authentication Setup Guide

> English: this page ・ 日本語: [AUTH_SETUP.ja.md](./AUTH_SETUP.ja.md)

geo-base currently uses its own **local provider** for authentication (`AUTH_PROVIDER=local`).
The provider abstraction (`api/lib/auth/provider.py`) is kept so the project can add another IdP later,
but **only `local` is supported today**.

> The old `AUTH_PROVIDER=supabase` setup was retired after the Fly Postgres migration and the
> removal of the Supabase Auth provider implementation. See [`docs/AUTH_MIGRATION.md`](./AUTH_MIGRATION.md)
> for the migration history.

This guide focuses on the **local and production setup steps**. For the higher-level design,
see [`docs/superpowers/specs/2026-05-08-pluggable-auth-design.md`](./superpowers/specs/2026-05-08-pluggable-auth-design.md).

Related docs:

- Manual pre-release E2E checks: [`docs/AUTH_E2E_CHECKLIST.md`](./AUTH_E2E_CHECKLIST.md)
- Authorization review: [`docs/ACCESS_CONTROL_REVIEW.md`](./ACCESS_CONTROL_REVIEW.md)
- Production database setup: [`docs/POSTGRES_SETUP.md`](./POSTGRES_SETUP.md)

---

## Quick Start

### 1. Start PostGIS

```bash
cd docker
docker compose up -d postgis
```

`docker/postgis-init/04_auth_schema.sql` creates the auth tables on first boot.

### 2. Set environment variables

Create `api/.env`:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base

AUTH_PROVIDER=local
JWT_SECRET=...   # generate a random secret, for example with: openssl rand -base64 64
JWT_AUDIENCE=authenticated
JWT_ISSUER=geo-base
ACCESS_TOKEN_TTL_SECONDS=900

EMAIL_BACKEND=console
INVITATION_BASE_URL=http://localhost:3000

CORS_ORIGINS=http://localhost:3000
COOKIE_SAMESITE=lax
COOKIE_SECURE=false

LOCAL_AUTH_ALLOW_SIGNUP=false
```

If `JWT_SECRET` is missing or too short, the API fails fast at startup.

### 3. Create the initial admin user

```bash
cd api
uv sync
uv run python -m lib.auth.cli create-admin --email admin@example.com
```

### 4. Start the API

```bash
cd api
uv run uvicorn lib.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

### 5. Start the Admin UI

```bash
cd app
npm install
npm run dev
```

Open http://localhost:3000/login and sign in with the admin user you created.

---

## API Endpoints

The auth routes live under `api/lib/routers/auth.py`. State-changing requests use a refresh cookie
plus a bearer access token.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | - | Log in with email and password |
| POST | `/api/auth/refresh` | Refresh cookie | Refresh the access token |
| POST | `/api/auth/logout` | Refresh cookie | Revoke the refresh token |
| GET | `/api/auth/me` | Bearer | Get the current user |
| PATCH | `/api/auth/me` | Bearer | Update name, email, or metadata |
| POST | `/api/auth/me/password` | Bearer | Change the password |
| POST | `/api/auth/password-reset/request` | - | Send a reset email |
| POST | `/api/auth/password-reset/confirm` | - | Set a new password from a reset token |
| GET | `/api/auth/invitations/{token}` | - | Read invitation details |
| POST | `/api/auth/accept-invitation` | - | Accept an invitation and create a new user |

The local base URL is `http://localhost:8000`. Production uses `https://geo-base-api.fly.dev`.

---

## API Key Usage

API keys are recommended for integrations such as CI uploads, automated sync jobs, and agent-driven updates.

### Scopes

| Scope | Operations |
|---|---|
| `read` | GET endpoints such as feature, tileset, and datasource reads |
| `write` | POST/PATCH endpoints such as create/update |
| `delete` | DELETE endpoints |

`write` includes `read`, `delete` includes `write`, and `admin` includes everything.

### Creating an API key

Use the Admin UI after login, or call the API directly with a JWT:

```bash
curl -X POST https://geo-base-api.fly.dev/api/api-keys \
  -H "Authorization: Bearer $JWT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ci-uploader",
    "scopes": ["read", "write"],
    "team_id": null
  }'
```

The returned `gb_live_xxx...` token is only visible at creation time.

### Write examples

```bash
# Update a personal tileset
curl -X PATCH https://geo-base-api.fly.dev/api/tilesets/$TILESET_ID \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "updated-name"}'

# Delete a tileset
curl -X DELETE https://geo-base-api.fly.dev/api/tilesets/$TILESET_ID \
  -H "Authorization: Bearer $DELETE_API_KEY"
```

Team API keys require the target shared tileset to grant the appropriate `team_tilesets.permission_level`.

### Common errors

| HTTP | Typical detail | Cause / fix |
|---|---|---|
| 401 | `Authentication required` | Check the `Authorization: Bearer ...` header |
| 403 | `write scope required ...` or `Not authorized to ...` | Reissue the key with the correct scopes or confirm resource authorization |
| 429 | `API key rate limit exceeded` | Wait, or inspect the configured rate limit |

### Rate limiting

API keys can have per-minute and per-day limits. The backend can use either the DB or Redis as the
rate-limit store. Redis uses a fail-open policy: if Redis is unavailable, requests are allowed and a
warning is logged.

For production, keep `REDIS_URL` healthy and monitor `/api/health/redis`.

---

## Environment Reference

### API (`api/.env`)

- `DATABASE_URL`
- `AUTH_PROVIDER=local`
- `JWT_SECRET`
- `JWT_AUDIENCE`
- `JWT_ISSUER`
- `ACCESS_TOKEN_TTL_SECONDS`
- `EMAIL_BACKEND`
- `INVITATION_BASE_URL`
- `CORS_ORIGINS`
- `COOKIE_SAMESITE`
- `COOKIE_SECURE`
- `LOCAL_AUTH_ALLOW_SIGNUP`

### Admin UI (`app/.env.local`)

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_MCP_URL`

### MCP Server (`mcp/.env`)

- `TILE_SERVER_URL`
- `DEBUG`
- `API_TOKEN`

---

## Troubleshooting

- If the API fails to start, confirm `JWT_SECRET` is set and long enough.
- If login fails, confirm the admin user exists and the Admin UI is pointing to the right API URL.
- If invitation or reset emails are not visible during development, use `EMAIL_BACKEND=console`.
