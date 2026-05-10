# geo-base-pg — Fly.io self-hosted PostGIS

Postgres 16 + PostGIS 3.4 を Fly Machine 1 ノードで運用する構成。
ベース image は `postgis/postgis:16-3.4`、Fly app 名は `geo-base-pg`、
リージョンは `nrt`（API と同じ Tokyo）。

```
pg/
├── Dockerfile   # postgis/postgis:16-3.4 + init スクリプトを焼き込み
├── fly.toml     # geo-base-pg app の Fly 設定
└── README.md    # ここ
```

## デプロイ・運用手順

詳細は [docs/POSTGRES_SETUP.md](../docs/POSTGRES_SETUP.md) を参照。
よくある操作だけ抜粋:

```fish
# 接続（ローカルから）
flyctl proxy 5433:5432 -a geo-base-pg
PGPASSWORD=$(flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD') \
  psql -h localhost -p 5433 -U postgres -d geo_base

# デプロイ
flyctl deploy --config pg/fly.toml -a geo-base-pg

# ログ
flyctl logs -a geo-base-pg

# Volume snapshot 一覧（自動 daily snapshot は 5 日保持）
flyctl volumes list -a geo-base-pg
flyctl volumes snapshots list <volume-id>
```

## 重要な留意点

- **public ネットワークに公開されていない**。他 Fly app からの内部接続だけ可能（`geo-base-pg.internal:5432`）。同じ org でないアプリからは到達不能。
- **HA なし**。マシン障害時は volume snapshot から復元する手順 (`docs/POSTGRES_SETUP.md`) を実行する。
- **論理破損対策**として、自動 volume snapshot に加えて GitHub Actions による週次 `pg_dump` を別途運用予定（[#issue TBD]）。
