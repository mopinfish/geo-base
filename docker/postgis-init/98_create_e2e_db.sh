#!/bin/bash
# Create geo_base_e2e database with the same schema as geo_base.
#
# Runs after all SQL init scripts (01_*..09_*) have populated the dev DB.
# Playwright E2E tests use this DB so that pytest's TRUNCATE fixtures
# (geo_base_test) and dev data (geo_base) are never touched.
#
# Numbered 98_ to run before 99_create_test_db.sh (alphabetical order).
#
# This script only runs on first container init (when the data volume is
# fresh). For existing volumes, create the DB manually:
#
#   docker compose -f docker/docker-compose.yml exec postgis \
#     psql -U postgres -c "CREATE DATABASE geo_base_e2e;"
#   docker compose -f docker/docker-compose.yml exec postgis bash -c \
#     'pg_dump -U postgres --schema-only --no-owner --no-acl geo_base \
#        | psql -U postgres -d geo_base_e2e'

set -euo pipefail

E2E_DB="${E2E_DATABASE_NAME:-geo_base_e2e}"
DEV_DB="${POSTGRES_DB:-geo_base}"

echo "[init] Creating E2E database: ${E2E_DB}"

psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres <<-EOSQL
	SELECT 'CREATE DATABASE ${E2E_DB}'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${E2E_DB}')\gexec
EOSQL

echo "[init] Cloning schema from ${DEV_DB} to ${E2E_DB}"

pg_dump -U "${POSTGRES_USER}" --schema-only --no-owner --no-acl "${DEV_DB}" \
	| psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${E2E_DB}"

echo "[init] E2E database ready: ${E2E_DB}"
