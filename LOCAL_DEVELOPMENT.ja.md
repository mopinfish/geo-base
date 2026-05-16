# geo-base ローカル開発環境

> English: [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) ・ 日本語: this page

このドキュメントでは、geo-base の各コンポーネントをローカル環境で実行する方法を説明します。

> 認証（`AUTH_PROVIDER=local`、初期管理者作成、トラブルシューティング）の詳細は
> [`docs/AUTH_SETUP.ja.md`](docs/AUTH_SETUP.ja.md) を参照してください。

## ポート割り当て

| コンポーネント | ポート | ディレクトリ | 説明 |
|---|---|---|---|
| Admin UI | 3000 | `/app` | Next.js 管理画面 |
| API | 8000 | `/api` | FastAPI タイルサーバー |
| MCP Server | stdio | `/mcp` | Claude Desktop 連携（デフォルト: stdio; SSE: `MCP_TRANSPORT=sse MCP_PORT=8001`） |

## 前提条件

- Node.js 18+
- Python 3.11+
- uv（Python パッケージマネージャー）
- PostgreSQL + PostGIS（`docker compose up -d postgis` で起動可。`docker/` 配下）

## 起動方法

### すべてのコンポーネントを起動（3 つのターミナル）

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

### Admin UI のみ起動（本番 API を使用）

```fish
cd app

# .env.local を本番向けに設定
echo 'NEXT_PUBLIC_API_URL=https://geo-base-api.fly.dev' > .env.local

npm run dev
```

### API のみ起動

```fish
cd api
uv run uvicorn lib.main:app --reload --port 8000
```

## 環境変数

### API (`/api/.env`)

```env
# データベース接続
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base

# 認証プロバイダ（local のみサポート。Supabase 対応は Issue #72 で廃止済み）
AUTH_PROVIDER=local

# JWT 設定（local モード必須。`openssl rand -base64 64` で生成）
JWT_SECRET=your-jwt-secret
JWT_AUDIENCE=authenticated
JWT_ISSUER=geo-base
ACCESS_TOKEN_TTL_SECONDS=900

# メール（招待・パスワードリセット）
EMAIL_BACKEND=console            # null / console / smtp
INVITATION_BASE_URL=http://localhost:3000

# CORS / Cookie
CORS_ORIGINS=http://localhost:3000
COOKIE_SAMESITE=lax
COOKIE_SECURE=false

# local プロバイダ固有
LOCAL_AUTH_ALLOW_SIGNUP=false    # 公開 signup を許可する場合のみ true
```

詳細な変数リファレンスは [`docs/AUTH_SETUP.ja.md`](docs/AUTH_SETUP.ja.md) を参照してください。

### MCP Server (`/mcp/.env`)

```env
TILE_SERVER_URL=http://localhost:8000
DEBUG=true
API_TOKEN=your-api-token
```

### Admin UI (`/app/.env.local`)

```env
# ローカル開発時
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MCP_URL=http://localhost:8001

# 本番 API を使う場合
# NEXT_PUBLIC_API_URL=https://geo-base-api.fly.dev
# NEXT_PUBLIC_MCP_URL=https://geo-base-mcp.fly.dev
```

## 動作確認

### API ヘルスチェック

```fish
# ローカル
curl http://localhost:8000/api/health

# 本番
curl https://geo-base-api.fly.dev/api/health
```

### タイルセット一覧

```fish
curl http://localhost:8000/api/tilesets
```

### Admin UI

ブラウザで http://localhost:3000 を開きます。

## トラブルシューティング

### ポートが既に使用されている

```fish
lsof -i :3000
lsof -i :8000
lsof -i :8001

# プロセスを終了
kill -9 <PID>
```

### CORS エラー

API がローカルで動作している場合、CORS は自動的に許可されます。
本番 API を使用する場合は、`.env.local` を本番 URL に設定してください。

### データベース接続エラー

```fish
# PostgreSQL が起動しているか確認
pg_isready -h localhost -p 5432

# Docker compose で起動していない場合
cd docker && docker compose up -d postgis
```

---

# Vercel デプロイ構成（Admin UI のみ）

> Vercel にデプロイするのは **Admin UI (Next.js) の `geo-base-admin` プロジェクトのみ**です。
> FastAPI タイルサーバーは現在 Fly.io (`geo-base-api`) でホストしており、
> 旧 Vercel API デプロイ (`geo-base` project) は廃止済みです（詳細は `api/FLY_DEPLOY.md`）。

## プロジェクト構成（参考）

| プロジェクト | プラットフォーム | Root Directory | URL | デプロイ手順 |
|---|---|---|---|---|
| `geo-base-admin` | **Vercel** | `app` | https://geo-base-admin.vercel.app | 本セクション |
| `geo-base-api` | Fly.io | `api` | https://geo-base-api.fly.dev | `api/FLY_DEPLOY.md` |
| `geo-base-mcp` | Fly.io | `mcp` | https://geo-base-mcp.fly.dev | `cd mcp && fly deploy` |
| `geo-base-pg` | Fly.io | `pg` | `geo-base-pg.internal` (internal) | `docs/POSTGRES_SETUP.ja.md` |

## Admin UI (Vercel) プロジェクトの作成手順

### 1. Vercel Dashboard で新規プロジェクト作成

1. [Vercel Dashboard](https://vercel.com/dashboard) にログイン
2. **Add New...** → **Project** をクリック
3. 同じリポジトリ `mopinfish/geo-base` を選択
4. **Import** をクリック

### 2. プロジェクト設定

| 設定項目 | 値 |
|---|---|
| Project Name | `geo-base-admin` |
| Framework Preset | `Next.js`（自動検出） |
| Root Directory | `app` |
| Build Command | デフォルトのまま |
| Output Directory | デフォルトのまま |

### 3. 環境変数の設定

| 変数名 | 値 | 説明 |
|---|---|---|
| `API_BACKEND_URL` | `https://geo-base-api.fly.dev` | **必須**。`next.config.ts` の rewrites が `/api/*` を proxy する宛先 |
| `NEXT_PUBLIC_API_URL` | （空） | 本番では同一オリジン fetch を使うため空にする |
| `NEXT_PUBLIC_MCP_URL` | `https://geo-base-mcp.fly.dev` | 本番 MCP URL |

### 4. デプロイ

**Deploy** をクリックしてデプロイを開始します。

### 5. 動作確認

- Admin UI: `https://geo-base-admin.vercel.app`
- API: `https://geo-base-api.fly.dev/api/health`

---

## 本番環境一覧

| サービス | URL | プラットフォーム |
|---|---|---|
| Admin UI | https://geo-base-admin.vercel.app | Vercel |
| API | https://geo-base-api.fly.dev | Fly.io |
| MCP Server | https://geo-base-mcp.fly.dev | Fly.io |
| PostgreSQL + PostGIS | `geo-base-pg.internal` (Fly internal network) | Fly.io (`geo-base-pg`) |
