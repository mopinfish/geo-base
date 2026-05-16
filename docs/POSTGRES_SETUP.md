# PostgreSQL Setup and Operations Guide

> English: this page ・ 日本語: [POSTGRES_SETUP.ja.md](./POSTGRES_SETUP.ja.md)

geo-base production uses a **single-node `postgis/postgis:16-3.4` database on Fly.io**.
This guide covers initial setup, connectivity, schema changes, backups, and recovery.

## Architecture

- The database is only reachable over Fly private networking at `geo-base-pg.internal:5432`
- There is no public DB endpoint
- The deployment uses PostgreSQL 16 + PostGIS 3.4, matching local development

## Initial Setup

### 1. Create the Fly app and volume

```fish
flyctl apps create geo-base-pg --org personal
flyctl volumes create pg_data --region nrt --size 10 --app geo-base-pg --yes
```

### 2. Set the database password

```fish
flyctl secrets set POSTGRES_PASSWORD=(openssl rand -base64 32 | tr -d '/+=' | head -c 32) -a geo-base-pg
```

Keep the password in a secret manager. Fly will not reveal it via the dashboard or `flyctl secrets list` (though it remains accessible to operators with SSH access via `flyctl ssh console`).

### 3. Deploy

```fish
flyctl deploy . --config pg/fly.toml -a geo-base-pg
```

The init SQL under `docker/postgis-init/` is baked into the image and runs on first boot.

### 4. Verify

```fish
flyctl logs -a geo-base-pg | grep -E 'database system is ready|CREATE TABLE'
```

To inspect the schema, use `flyctl proxy` and `psql`:

```fish
flyctl proxy 5433:5432 -a geo-base-pg &
set PG_PROXY_PID $last_pid
sleep 2
set PG_PASS (flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1)
env PGPASSWORD=$PG_PASS psql -h localhost -p 5433 -U postgres -d geo_base -c '\dt'
kill $PG_PROXY_PID
```

### 5. Update API secrets

```fish
set DATABASE_URL "postgresql://postgres:$PG_PASS@geo-base-pg.internal:5432/geo_base"
flyctl secrets set DATABASE_URL=$DATABASE_URL -a geo-base-api
flyctl secrets set AUTH_PROVIDER=local -a geo-base-api
flyctl secrets set JWT_SECRET=(openssl rand -base64 64) -a geo-base-api
```

Remove any obsolete Supabase-related secrets from the API app.

### 6. Redeploy the API

```fish
cd api && flyctl deploy
```

## Daily Operations

- Use `flyctl proxy 5433:5432 -a geo-base-pg` for local admin access
- Check status with `flyctl status -a geo-base-pg`, `flyctl logs -a geo-base-pg`, and `flyctl machine list -a geo-base-pg`
- Apply schema changes manually with `psql -f path/to/migration.sql`

## Backups and Recovery

- Fly volumes take daily snapshots and keep them for 5 days
- Use `pg_dump` for logical backups
- Restore from a snapshot when the machine or volume is damaged
- Restore from `pg_dump` when the schema or data is logically corrupted

## Failure Scenarios

- If only the machine fails, restart it with `flyctl machine restart`
- If the volume is damaged, create a new volume from a snapshot
- If the data is logically corrupted, restore into a clean database from a dump

For detailed recovery commands and operational notes, see the Japanese version of this document.
