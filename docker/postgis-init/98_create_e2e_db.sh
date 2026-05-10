#!/bin/bash
# Create geo_base_e2e (Phase 1) and optional worker DBs (geo_base_e2e_w0..w(N-1)).
# Issue #111: Phase 2 でワーカー並列化の足場を作る（実際の workers: 4 化は
# 後段で実施）。E2E_WORKER_COUNT で並列度を指定（デフォルト 1 = 単一 DB のみ）。
#
# Numbered 98_ to run before 99_create_test_db.sh (alphabetical order).
#
# This script only runs on first container init (when the data volume is fresh).
# For existing volumes, create the DBs manually:
#
#   docker compose -f docker/docker-compose.yml exec postgis \
#     psql -U postgres -c "CREATE DATABASE geo_base_e2e;"
#   docker compose -f docker/docker-compose.yml exec postgis bash -c \
#     'pg_dump -U postgres --schema-only --no-owner --no-acl geo_base \
#        | psql -U postgres -d geo_base_e2e'

set -euo pipefail

DEV_DB="${POSTGRES_DB:-geo_base}"
WORKER_COUNT="${E2E_WORKER_COUNT:-1}"

# Phase 1 互換: geo_base_e2e は常に作る。
DBS=("geo_base_e2e")

# Phase 2 (worker count > 1): w0..w(N-1) を追加で作る。
if [ "$WORKER_COUNT" -gt 1 ]; then
  for i in $(seq 0 $((WORKER_COUNT - 1))); do
    DBS+=("geo_base_e2e_w${i}")
  done
fi

for DB in "${DBS[@]}"; do
  echo "[init] Creating E2E database: ${DB}"
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres <<-EOSQL
	SELECT 'CREATE DATABASE ${DB}'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB}')\gexec
EOSQL
  echo "[init] Cloning schema from ${DEV_DB} to ${DB}"
  pg_dump -U "${POSTGRES_USER}" --schema-only --no-owner --no-acl "${DEV_DB}" \
    | psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${DB}"
  echo "[init] E2E database ready: ${DB}"
done
