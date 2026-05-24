# geo-base

> 🌐 **English**: [README.md](./README.md) ・ **日本語**: this page

モノレポ構成の地理空間タイルサーバーシステム

## 概要

geo-baseは、地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムです。

### 主要機能

1. **タイルサーバー**: ラスタ/ベクタタイルの配信API
2. **MCPサーバー**: Claude等のAIクライアント向けツール提供
3. **管理画面**: タイルセットのアップロード・管理・プレビュー

## 技術スタック

### バックエンド
- **タイルサーバー**: Python FastAPI (Fly.io)
- **MCPサーバー**: Python FastMCP (Fly.io / ローカル)
- **データベース**: PostgreSQL + PostGIS (Fly.io `geo-base-pg`)
- **ストレージ**: Fly Tigris (S3 互換、Issue #72 で 2026-05-10 に Supabase Storage から完全移行）。private bucket 運用で、新規 upload は `s3://bucket/path` 形式の内部 URL として保存される（Issue #101）。
- **キャッシュ**: Redis (Upstash、Issue #119 で 2026-05-11 に Python 依存追加。稼働状況は `GET /api/health/redis` で確認可能)

### フロントエンド
- **管理画面**: Next.js + TypeScript (Vercel)
- **地図ライブラリ**: MapLibre GL JS
- **認証**: 自前の local provider（JWT 発行 + bcrypt、`AUTH_PROVIDER=local`）

## ディレクトリ構成

```
geo-base/
├── api/                 # FastAPI タイルサーバー
├── app/                 # Next.js 管理画面
├── mcp/                 # MCP Server
├── docker/              # ローカル開発用Docker
├── scripts/             # ユーティリティスクリプト
└── packages/            # 共有パッケージ
```

## ドキュメント

- デプロイガイド: [DEPLOY.ja.md](./docs/manuals/DEPLOY.ja.md)
- ローカル開発: [LOCAL_DEVELOPMENT.ja.md](./docs/manuals/LOCAL_DEVELOPMENT.ja.md)
- 認証セットアップ: [docs/AUTH_SETUP.ja.md](./docs/AUTH_SETUP.ja.md)
- PostgreSQL セットアップ: [docs/POSTGRES_SETUP.ja.md](./docs/POSTGRES_SETUP.ja.md)
- Redis セットアップ: [docs/REDIS_SETUP.ja.md](./docs/REDIS_SETUP.ja.md)
- アクセス制御レビュー: [docs/ACCESS_CONTROL_REVIEW.ja.md](./docs/ACCESS_CONTROL_REVIEW.ja.md)
- 動作確認手順: [TESTING.ja.md](./docs/manuals/TESTING.ja.md)

## ローカル開発環境セットアップ

### 前提条件

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- uv（Pythonパッケージマネージャー）

### uvのインストール

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# または pip
pip install uv
```

### セットアップ手順

```bash
# リポジトリクローン
git clone https://github.com/mopinfish/geo-base.git
cd geo-base

# ローカルPostGIS起動
cd docker
docker compose up -d
cd ..

# APIサーバー環境構築
cd api
uv sync
uv run uvicorn lib.main:app --reload --port 8000
cd ..

# MCPサーバー環境構築
cd mcp
uv sync
uv run python server.py
cd ..

# 管理画面環境構築
cd app
npm install
npm run dev
cd ..
```

### 環境変数

3 つのサービスディレクトリ (`api/`, `app/`, `mcp/`) にそれぞれ `.env.example` があります。ランタイムが読む場所にコピーしてください:

- `api/` と `mcp/` (Python): `.env.example` を `.env` にコピー
- `app/` (Next.js): `.env.example` を `.env.local` にコピー。Next.js 自体は `.env` も読み込みますが、本リポジトリでは Admin UI 専用のローカル設定を git 管理外に保つため `.env.local` を使う運用にしています (Next.js scaffold は `.env.local` をデフォルトで gitignore する)。

## サポートフォーマット

### ラスタタイル
- GeoTIFF / Cloud Optimized GeoTIFF (COG)
- PNG
- データPNG（標高データ等）
- JPG

### ベクタタイル
- GeoJSON
- Mapbox Vector Tile (MVT / .pbf)
- MBTiles
- PMTiles

## ライセンス

MIT License — [LICENSE](./LICENSE) を参照してください。
