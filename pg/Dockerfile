# =============================================================================
# geo-base PostGIS — self-hosted on Fly.io
# =============================================================================
# Postgres 16 + PostGIS 3.4. Init scripts under docker/postgis-init/ are
# copied into /docker-entrypoint-initdb.d/, so on the *first* boot (when
# PGDATA is empty) the official postgres entrypoint executes them in
# numeric order.
#
# 意図的に除外しているファイル:
# - 99_create_test_db.sh: pytest 用 geo_base_test を作るスクリプトで本番には不要
# - 09_rls_policies.sql: ローカル開発用の allow-all RLS（`USING (true)`）。本番は
#   API のアプリ層で authz を行う設計のため RLS は使わない。仮にこのファイルを
#   焼き込むと、将来 postgres 以外のロール（read-only 分析用など）を追加した際に
#   「RLS が有効化されているのに該当ロール用のポリシーが無い → アクセス遮断」
#   になりがちなので、本番では RLS そのものを有効化しない。
#
# スキーマ変更後の差分は flyctl proxy + psql で手動適用する。
# =============================================================================

FROM postgis/postgis:16-3.4

COPY docker/postgis-init/01_init.sql              /docker-entrypoint-initdb.d/
COPY docker/postgis-init/02_raster_schema.sql     /docker-entrypoint-initdb.d/
COPY docker/postgis-init/03_pmtiles_schema.sql    /docker-entrypoint-initdb.d/
COPY docker/postgis-init/04_auth_schema.sql       /docker-entrypoint-initdb.d/
COPY docker/postgis-init/05_teams_schema.sql      /docker-entrypoint-initdb.d/
COPY docker/postgis-init/06_api_keys_schema.sql   /docker-entrypoint-initdb.d/
COPY docker/postgis-init/07_preferred_locale.sql  /docker-entrypoint-initdb.d/
