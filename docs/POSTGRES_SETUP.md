# PostgreSQL (Fly.io 自前ホスティング) セットアップ・運用ガイド

geo-base 本番 DB は **Fly Machine 上の `postgis/postgis:16-3.4` 単一ノード**で運用する。
本ドキュメントは初期構築・接続方法・スキーマ変更・バックアップ運用・障害復旧をひと通りカバーする。

> **背景**: 元々 Supabase Free Plan の `geo-base` プロジェクトを使っていたが、
> 2024-06-24 から長期 paused 状態となりダッシュボード経由での復旧が不可能になった
> ため、Phase 3（Step 3.3-A）で Supabase Auth 依存を廃した実装が揃ったタイミングで
> Fly.io 内に自前 Postgres を置く構成に移行した（2026-05-10）。

## アーキテクチャ概要

```
┌─────────────────┐  6PN (private IPv6)   ┌──────────────────┐
│  geo-base-api   │ ────────────────────▶ │   geo-base-pg    │
│  (Fly app)      │                       │ (Fly app)        │
│  in nrt         │                       │ postgis/postgis  │
└─────────────────┘                       │ :16-3.4 in nrt   │
                                          └────────┬─────────┘
                                                   │ persistent
                                                   ▼
                                          ┌──────────────────┐
                                          │  Volume "pg_data"│
                                          │  10 GB, in nrt   │
                                          │  daily snapshot  │
                                          └──────────────────┘
```

- **Public 公開なし**: `geo-base-pg.internal:5432` でのみ到達可能（同 Fly org の app のみ）
- **HA 無し**: 単一マシン。マシン障害時は volume snapshot から復元する
- **PostgreSQL 16 + PostGIS 3.4**: ローカル開発の `docker compose` と完全一致

## 1. 初期構築（再構築時にも再現可能）

repo root から実行する想定。

### 1.1. Fly app と volume を作成

```fish
# app
flyctl apps create geo-base-pg --org personal

# volume (10GB, nrt region)
flyctl volumes create pg_data \
    --region nrt \
    --size 10 \
    --app geo-base-pg \
    --yes
```

### 1.2. Postgres パスワードを secret として設定

```fish
flyctl secrets set POSTGRES_PASSWORD=(openssl rand -base64 32 | tr -d '/+=' | head -c 32) \
    -a geo-base-pg
```

> **重要**: パスワードは `1Password` 等の secret マネージャに必ず控えておく。
> Fly の secrets list は digest しか表示しないため、忘れると recovery 不能。

### 1.3. デプロイ

```fish
flyctl deploy --config pg/fly.toml --dockerfile pg/Dockerfile -a geo-base-pg
```

`Dockerfile` で `docker/postgis-init/0[1-9]_*.sql` を `/docker-entrypoint-initdb.d/`
に焼き込んでいるため、**初回起動時に空のボリュームを検知して全スキーマが自動投入される**。

### 1.4. 動作確認

```fish
# ログでスキーマ投入が完了したか確認
flyctl logs -a geo-base-pg | grep -E 'database system is ready|CREATE TABLE'

# psql で接続して確認
flyctl proxy 5433:5432 -a geo-base-pg &
PG_PROXY_PID=$last_pid
sleep 2

# パスワードを取得（マシン内環境変数を覗く）
set PG_PASS (flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1)

env PGPASSWORD=$PG_PASS psql -h localhost -p 5433 -U postgres -d geo_base \
    -c '\dt' \
    -c "SELECT extname FROM pg_extension WHERE extname LIKE 'postgis%';"

# 後片付け
kill $PG_PROXY_PID
```

期待される出力には `team_invitations`, `tilesets`, `users` 等の table と、
`postgis` 拡張がリストされる。

### 1.5. API 側の secret 切り替え

```fish
# API 用接続文字列（6PN 経由、`.internal` は同 org の app から到達可能）
set DATABASE_URL "postgresql://postgres:$PG_PASS@geo-base-pg.internal:5432/geo_base"

flyctl secrets set DATABASE_URL=$DATABASE_URL -a geo-base-api
flyctl secrets set AUTH_PROVIDER=local -a geo-base-api
flyctl secrets set JWT_SECRET=(openssl rand -base64 64) -a geo-base-api

# Supabase 関連 secret は不要なので削除
flyctl secrets unset SUPABASE_URL SUPABASE_JWT_SECRET -a geo-base-api
```

### 1.6. API の再デプロイ

```fish
cd api && flyctl deploy
```

deploy 後、Fly app の health check が通れば移行完了。

## 2. 日常運用

### 2.1. 接続（管理目的）

公開ポートは無いため、ローカルから直接接続するには `flyctl proxy` を使う。

```fish
flyctl proxy 5433:5432 -a geo-base-pg
# 別ターミナルで
env PGPASSWORD=(flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1) \
    psql -h localhost -p 5433 -U postgres -d geo_base
```

または Fly Machine 内で直接 psql を叩く:

```fish
flyctl ssh console -a geo-base-pg
# machine 内で
psql -U postgres -d geo_base
```

### 2.2. ログ・状態確認

```fish
flyctl status -a geo-base-pg
flyctl logs -a geo-base-pg
flyctl machine list -a geo-base-pg
```

### 2.3. スキーマ変更（マイグレーション）

`docker/postgis-init/*.sql` は **初回ボリューム作成時にしか走らない**。
本番への変更は手動で適用する。

```fish
# 1. ローカルで変更内容を docker/postgis-init/*.sql に反映（次回 fresh init で取り込まれる）
# 2. 本番に DDL を適用
flyctl proxy 5433:5432 -a geo-base-pg
env PGPASSWORD=(flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1) \
    psql -h localhost -p 5433 -U postgres -d geo_base -f path/to/migration.sql
```

冪等な書き方（`IF NOT EXISTS`、`CREATE OR REPLACE` 等）にしておくと再実行に強い。

## 3. バックアップ・復旧

### 3.1. Layer 1: Fly Volume の自動 snapshot

Fly は volume の **daily snapshot を自動取得し 5 日保持** する。設定は不要。

```fish
# snapshot 一覧
flyctl volumes list -a geo-base-pg
flyctl volumes snapshots list <volume-id>

# snapshot から新規 volume を作成（既存 volume を上書きはしない）
flyctl volumes create pg_data_restored \
    --region nrt \
    --snapshot-id <snapshot-id> \
    -a geo-base-pg
```

これで「マシン故障 / ボリューム破損」レベルの障害は復旧可能。
**保持期間が 5 日と短いことに注意** —より長い保管を欲する場合は次の Layer 2 を併用。

### 3.2. Layer 2: 論理バックアップ（pg_dump）

論理破損（誤った TRUNCATE、スキーマ migration 失敗等）に備える。

#### 手動実行（緊急バックアップ）

```fish
flyctl proxy 5433:5432 -a geo-base-pg &
env PGPASSWORD=(flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1) \
    pg_dump -h localhost -p 5433 -U postgres -d geo_base -F c \
    > geo_base_(date -u +%Y%m%dT%H%M%SZ).dump
```

#### 定期実行（運用化）

将来的に GitHub Actions schedule で `pg_dump` → Tigris (Fly のS3互換ストレージ) に
weekly push する仕組みを追加予定（PR #70 の cleanup-expired と同じパターン）。

## 4. 障害復旧シナリオ

### 4.1. マシンのみ故障（ボリューム生存）

通常は Fly が自動で再起動する。手動で対応する場合:

```fish
flyctl machine list -a geo-base-pg
flyctl machine restart <machine-id> -a geo-base-pg
```

### 4.2. ボリューム破損 → 自動 snapshot から復元

```fish
# 1. 破損 volume の snapshot 一覧から復元したい時点の id を選ぶ
flyctl volumes list -a geo-base-pg                # broken volume id 確認
flyctl volumes snapshots list <broken-volume-id>  # snapshot 一覧

# 2. snapshot から新しい volume を作成
flyctl volumes create pg_data_new \
    --region nrt --size 10 --snapshot-id <snapshot-id> -a geo-base-pg

# 3. fly.toml の `[mounts] source` を一時的に新ボリューム名に変更してデプロイ
#    （または既存マシンを destroy して新ボリュームで machine run）
```

### 4.3. 論理破損 → pg_dump から復元

```fish
# 0. flyctl proxy をバックグラウンドで起動（5433 → 5432 のローカル転送）
flyctl proxy 5433:5432 -a geo-base-pg &
set PG_PROXY_PID $last_pid
sleep 2

# 1. 新しい空の DB に restore
set -lx PGPASSWORD (flyctl ssh console -a geo-base-pg -C 'printenv POSTGRES_PASSWORD' | tail -1)
psql -h localhost -p 5433 -U postgres -c 'CREATE DATABASE geo_base_restore'
pg_restore -h localhost -p 5433 -U postgres -d geo_base_restore geo_base_*.dump

# 2. 動作確認後、API の DATABASE_URL を新 DB に切替か、本番 DB を rename して入れ替え

# 3. proxy を終了
kill $PG_PROXY_PID
```

## 5. スケールアップ・将来の検討事項

| 状況 | 対応 |
|---|---|
| メモリが足りない | `[[vm]] memory = "2gb"` に変更して `flyctl deploy`。再起動が走る |
| ストレージが足りない | `flyctl volumes extend <id> --size <new-gb>` で拡張（縮小は不可） |
| HA が必要になった | Fly Managed Postgres ($38/月〜) に migrate するか、leader/replica 構成を自分で組む |
| バックアップ自動化 | GitHub Actions + `pg_dump` + Tigris 連携を実装する（[#issue TBD]） |
| pg_cron 等の追加拡張 | Dockerfile を `FROM postgis/postgis:16-3.4` ベースで RUN apt-get install で拡張 |

## 6. 参考リンク

- 公式 image: https://hub.docker.com/r/postgis/postgis
- Fly Volumes: https://fly.io/docs/volumes/
- Fly 6PN networking: https://fly.io/docs/networking/private-networking/
- Phase 3 の認証移行記録: `docs/AUTH_MIGRATION.md`
- インフラ移行検討: `docs/INFRA_MIGRATION_INVESTIGATION.md`
