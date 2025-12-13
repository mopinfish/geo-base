# geo-base ローカル開発環境

このドキュメントでは、geo-baseの各コンポーネントをローカル環境で実行する方法を説明します。

## ポート割り当て

| コンポーネント | ポート | ディレクトリ | 説明 |
|--------------|--------|-------------|------|
| **Admin UI** | 3000 | `/app` | Next.js 管理画面 |
| **API** | 8000 | `/api` | FastAPI タイルサーバー |
| **MCP Server** | 8001 | `/mcp` | Claude Desktop連携（SSEモード） |

## 前提条件

- Node.js 18+
- Python 3.12+
- uv (Python パッケージマネージャー)
- PostgreSQL + PostGIS（Supabaseを使用する場合は不要）

## 起動方法

### すべてのコンポーネントを起動（3つのターミナル）

```fish
# ターミナル1: API (FastAPI)
cd api
uv run uvicorn lib.main:app --reload --port 8000

# ターミナル2: MCP Server（必要な場合）
cd mcp
set -x TILE_SERVER_URL http://localhost:8000
uv run python server.py

# ターミナル3: Admin UI (Next.js)
cd app
npm run dev
```

### Admin UIのみ起動（本番APIを使用）

```fish
cd app

# .env.local を本番向けに設定
echo 'NEXT_PUBLIC_API_URL=https://geo-base-puce.vercel.app' > .env.local

npm run dev
```

### APIのみ起動

```fish
cd api
uv run uvicorn lib.main:app --reload --port 8000
```

## 環境変数

### API (`/api/.env`)

```env
# データベース接続
DATABASE_URL=postgresql://user:pass@localhost:5432/geo_base

# Supabase（本番環境）
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# JWT設定
JWT_SECRET=your-jwt-secret
```

### MCP Server (`/mcp/.env`)

```env
# タイルサーバーURL
TILE_SERVER_URL=http://localhost:8000

# デバッグモード
DEBUG=true

# 認証（必要な場合）
API_TOKEN=your-api-token
```

### Admin UI (`/app/.env.local`)

```env
# ローカル開発時
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MCP_URL=http://localhost:8001

# 本番APIを使う場合
# NEXT_PUBLIC_API_URL=https://geo-base-puce.vercel.app
# NEXT_PUBLIC_MCP_URL=https://geo-base-mcp.fly.dev
```

## 動作確認

### API ヘルスチェック

```fish
# ローカル
curl http://localhost:8000/api/health

# 本番
curl https://geo-base-puce.vercel.app/api/health
```

### タイルセット一覧

```fish
curl http://localhost:8000/api/tilesets
```

### Admin UI

ブラウザで http://localhost:3000 を開く

## トラブルシューティング

### ポートが既に使用されている

```fish
# 使用中のポートを確認
lsof -i :3000
lsof -i :8000
lsof -i :8001

# プロセスを終了
kill -9 <PID>
```

### CORS エラー

APIがローカルで動作している場合、CORSは自動的に許可されます。
本番APIを使用する場合は、`.env.local`を本番URLに設定してください。

### データベース接続エラー

ローカルPostgreSQLを使用する場合:
```fish
# PostgreSQLが起動しているか確認
pg_isready -h localhost -p 5432
```

Supabaseを使用する場合:
- Supabaseダッシュボードで接続情報を確認
- 環境変数が正しく設定されているか確認

## 本番環境

| サービス | URL |
|---------|-----|
| Admin UI | （Vercelにデプロイ予定） |
| API | https://geo-base-puce.vercel.app |
| MCP Server | https://geo-base-mcp.fly.dev |
