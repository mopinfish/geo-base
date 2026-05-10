# =============================================================================
# geo-base PostGIS — self-hosted on Fly.io
# =============================================================================
# Postgres 16 + PostGIS 3.4. Init scripts under docker/postgis-init/ are
# copied into /docker-entrypoint-initdb.d/, so on the *first* boot (when
# PGDATA is empty) the official postgres entrypoint executes them in
# numeric order.
#
# 99_create_test_db.sh は意図的に除外（pytest 用 geo_base_test を作るスクリプトで
# 本番には不要）。スキーマ変更後の差分は flyctl proxy + psql で手動適用する。
# =============================================================================

FROM postgis/postgis:16-3.4

COPY docker/postgis-init/01_init.sql            /docker-entrypoint-initdb.d/
COPY docker/postgis-init/02_raster_schema.sql   /docker-entrypoint-initdb.d/
COPY docker/postgis-init/03_pmtiles_schema.sql  /docker-entrypoint-initdb.d/
COPY docker/postgis-init/04_auth_schema.sql     /docker-entrypoint-initdb.d/
COPY docker/postgis-init/05_teams_schema.sql    /docker-entrypoint-initdb.d/
COPY docker/postgis-init/06_api_keys_schema.sql /docker-entrypoint-initdb.d/
COPY docker/postgis-init/09_rls_policies.sql    /docker-entrypoint-initdb.d/
