# geo-base API - Fly.io デプロイガイド

## 概要

geo-base APIをFly.ioにデプロイする手順を説明します。Fly.ioを使用することで、GDAL/rasterioなどのネイティブ依存を持つライブラリを完全にサポートできます。

## 前提条件

- [Fly.io CLI](https://fly.io/docs/hands-on/install-flyctl/) がインストールされていること
- Fly.ioアカウントを持っていること
- Fly Postgres (`geo-base-pg`) がデプロイ済みであること（`docs/POSTGRES_SETUP.md` 参照）

## 初回セットアップ

### 1. Fly.io CLIにログイン

```fish
fly auth login
```

### 2. アプリケーションの作成

```fish
cd api
fly apps create geo-base-api
```

### 3. シークレット（環境変数）の設定

```fish
# データベース接続文字列（Fly internal network 経由、`docs/POSTGRES_SETUP.md` と同じ
# `geo-base-pg.internal` ホスト名を使用。`geo-base-pg.flycast` も `api/lib/database.py`
# 側で受け付けるが、ドキュメントは `.internal` で統一する）
fly secrets set DATABASE_URL="postgresql://postgres:<PASSWORD>@geo-base-pg.internal:5432/geo_base"

# 認証（fish のコマンド置換は `(...)` なので、`openssl rand` は別シェル実行→値を貼る方式が無難）
set jwt_secret (openssl rand -base64 64)
fly secrets set AUTH_PROVIDER=local JWT_SECRET="$jwt_secret"

# ストレージ設定（COG/PMTiles アップロード backend、Fly Tigris）
# Issue #72 で 2026-05-10 に Supabase Storage から移行済み。private bucket 運用。
# flyctl storage create -a geo-base-api で bucket 作成すると以下の env が
# 自動セットされる: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_ENDPOINT_URL_S3 /
# AWS_REGION / BUCKET_NAME。これらは flyctl が直接 secrets として登録する。
flyctl storage create -a geo-base-api
# 上記が登録する env のうち、本 API が読むのは AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY (boto3 標準) と S3_ENDPOINT_URL (≒ AWS_ENDPOINT_URL_S3) /
# S3_REGION / S3_BUCKET (lib/config.py の Settings)。flyctl が登録する名前と
# 揃わない場合は明示的に上書きする:
fly secrets set S3_BUCKET="geo-base-tiles"
fly secrets set S3_ENDPOINT_URL="https://fly.storage.tigris.dev"
fly secrets set S3_REGION="auto"
# 任意: 公開 CDN 経由配信で URL prefix を変えたい場合のみ
# fly secrets set S3_PUBLIC_BASE_URL="https://cdn.example.com"
```

### 4. デプロイ

```fish
fly deploy
```

## デプロイ後の確認

### ヘルスチェック

```fish
# APIヘルスチェック
curl https://geo-base-api.fly.dev/api/health

# DBヘルスチェック
curl https://geo-base-api.fly.dev/api/health/db
```

### ログの確認

```fish
fly logs
```

### ステータス確認

```fish
fly status
```

## 更新デプロイ

コードを更新した後のデプロイ:

```fish
cd api
fly deploy
```

## スケーリング

### マシン数の調整

```fish
# 最小マシン数を1に設定（常時起動）
fly scale count 1

# 自動スケーリングを使用
fly scale count 0  # auto_start/stop を有効化
```

### メモリ/CPUの調整

```fish
# メモリを1GBに増加
fly scale memory 1024

# CPUコアを増加
fly scale vm shared-cpu-2x
```

## トラブルシューティング

### データベース接続エラー

1. シークレットが正しく設定されているか確認:
   ```fish
   fly secrets list
   ```

2. `DATABASE_URL` に `geo-base-pg.internal` 経由の Fly internal network ホスト名が含まれているか確認（`api/lib/database.py` は `*.internal` / `*.flycast` の両方を受け付けるが、`docs/POSTGRES_SETUP.md` と本書は `.internal` で統一）

3. Fly internal network (`*.internal` / `*.flycast`) は SSL 不要（`api/lib/database.py` で SSL を自動付与しないよう gate 済み、PR #76）。外部 PostgreSQL を使う場合のみ `?sslmode=require` を付ける

### メモリ不足エラー

ラスタータイル生成は多くのメモリを使用します:

```fish
fly scale memory 1024  # 1GBに増加
# または
fly scale memory 2048  # 2GBに増加
```

### 起動に時間がかかる

GDALイメージは大きいため、初回起動に時間がかかる場合があります。ヘルスチェックのgrace periodを調整:

```toml
# fly.toml
[[services.http_checks]]
  grace_period = "30s"  # 30秒に延長
```

## 本番環境の推奨設定

### 高可用性設定

```fish
# 2台のマシンを東京とシンガポールに配置
fly scale count 2 --region nrt,sin
```

### カスタムドメイン

```fish
# カスタムドメインの追加
fly certs add api.example.com

# DNS設定
# CNAME: api.example.com -> geo-base-api.fly.dev
```

## 関連リソース

- [Fly.io Documentation](https://fly.io/docs/)
- [Fly.io Python](https://fly.io/docs/languages-and-frameworks/python/)
- [geo-base メインドキュメント](../README.md)

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2025-12-16 | 初版作成 (Season 3 Step 3.1-A) |
