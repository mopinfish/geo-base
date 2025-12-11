# geo-base

モノレポ構成の地理空間タイルサーバーシステム

## 概要

geo-baseは、地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムです。

### 主要機能

1. **タイルサーバー**: ラスタ/ベクタタイルの配信API
2. **MCPサーバー**: Claude等のAIクライアント向けツール提供
3. **管理画面**: タイルセットのアップロード・管理・プレビュー

## 技術スタック

### バックエンド
- **タイルサーバー**: Python FastAPI (Vercel Serverless Functions)
- **MCPサーバー**: Python FastMCP (Fly.io / ローカル)
- **データベース**: PostgreSQL + PostGIS (Supabase)
- **ストレージ**: Vercel Blob

### フロントエンド
- **管理画面**: Next.js + TypeScript (Vercel)
- **地図ライブラリ**: MapLibre GL JS
- **認証**: Supabase Auth

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
git clone https://github.com/your-org/geo-base.git
cd geo-base

# ローカルPostGIS起動
cd docker
docker compose up -d
cd ..

# APIサーバー環境構築
cd api
uv sync
uv run uvicorn lib.main:app --reload --port 3000
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

各ディレクトリに`.env`ファイルを作成してください。テンプレートは`.env.example`を参照してください。

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

MIT License
