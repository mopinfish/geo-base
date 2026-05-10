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
# データベース接続文字列（Fly Postgres を Fly internal network 経由で参照）
fly secrets set DATABASE_URL="postgresql://postgres:<PASSWORD>@geo-base-pg.flycast:5432/geo_base"

# 認証
fly secrets set AUTH_PROVIDER=local
fly secrets set JWT_SECRET=$(openssl rand -base64 64)

# ストレージ設定（COG/PMTiles アップロード backend、Fly Tigris を想定。Issue #72 Phase 1.2 で詳細を確定予定）
# fly secrets set TIGRIS_BUCKET="geo-tiles"
# fly secrets set AWS_ACCESS_KEY_ID="..."
# fly secrets set AWS_SECRET_ACCESS_KEY="..."
# fly secrets set AWS_ENDPOINT_URL_S3="https://fly.storage.tigris.dev"
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

2. `DATABASE_URL` に `geo-base-pg.flycast` 経由の Fly internal network ホスト名が含まれているか確認

3. Fly internal network (`*.flycast` / `*.internal`) は SSL 不要（`api/lib/database.py` で SSL を自動付与しないよう gate 済み、PR #76）。外部 PostgreSQL を使う場合のみ `?sslmode=require` を付ける

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
