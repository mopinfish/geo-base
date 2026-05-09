#!/bin/bash
# Create geo_base_test database with the same schema as geo_base.
#
# Runs after all SQL init scripts (01_*..09_*) have populated the dev DB
# (geo_base = $POSTGRES_DB). Tests use TEST_DATABASE_URL pointing here so
# pytest's TRUNCATE fixtures never touch dev data (issue #47).
#
# This script only runs on first container init (when the data volume is
# fresh). For existing volumes, create the test DB manually:
#
#   docker compose exec postgis psql -U postgres -c "CREATE DATABASE geo_base_test;"
#   docker compose exec postgis bash -c \
#     'pg_dump -U postgres --schema-only geo_base | psql -U postgres -d geo_base_test'

set -euo pipefail

TEST_DB="${TEST_DATABASE_NAME:-geo_base_test}"
DEV_DB="${POSTGRES_DB:-geo_base}"

echo "[init] Creating test database: ${TEST_DB}"

psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres <<-EOSQL
	SELECT 'CREATE DATABASE ${TEST_DB}'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${TEST_DB}')\gexec
EOSQL

echo "[init] Cloning schema from ${DEV_DB} to ${TEST_DB}"

pg_dump -U "${POSTGRES_USER}" --schema-only --no-owner --no-acl "${DEV_DB}" \
	| psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${TEST_DB}"

echo "[init] Test database ready: ${TEST_DB}"
