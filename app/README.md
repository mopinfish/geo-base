# geo-base Admin UI

geo-base タイルサーバーの管理画面です。

## 技術スタック

- **フレームワーク**: Next.js 16 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS v4
- **UIコンポーネント**: shadcn/ui (手動セットアップ)
- **アイコン**: Lucide React

## ポート割り当て

| コンポーネント | ポート | 説明 |
|--------------|--------|------|
| Admin UI (Next.js) | 3000 | フロントエンド |
| API (FastAPI) | 8000 | バックエンドAPI |
| MCP Server | 8001 | Claude Desktop連携（SSEモード） |

## 開発環境のセットアップ

### 1. 依存関係のインストール

```bash
cd app
npm install
```

### 2. 環境変数の設定

`.env.local` を作成（`.env.example` を参考に）:

```env
# ローカル開発時
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MCP_URL=http://localhost:8001
```

> 本番 (Vercel) では Cookie ベース認証のため Admin UI 自身の origin から `/api/*` を叩く同一オリジン構成にしている。
> `next.config.ts` の rewrites が `API_BACKEND_URL`（server-side env）を proxy 先として参照する。
> Vercel project の Environment Variables では:
> - **`API_BACKEND_URL`** = `https://geo-base-api.fly.dev` （Production scope に設定。未設定だと build が fail-fast で停止）
> - **`NEXT_PUBLIC_API_URL`** = 空（client.ts は同一オリジン fetch するため）

> Phase 3 / Step 3.3-A 以降、Admin UI は API の `/api/auth/*` 経由で認証します。
> 認証バックエンドのセットアップは [`docs/AUTH_SETUP.md`](../docs/AUTH_SETUP.md) を参照。

### 3. ローカル開発サーバーの起動

**全コンポーネントを起動する場合（3つのターミナルを使用）:**

```fish
# ターミナル1: API起動 (ポート8000)
cd /path/to/geo-base/api
uv run uvicorn lib.main:app --reload --port 8000

# ターミナル2: MCP起動 (ポート8001、必要な場合)
cd /path/to/geo-base/mcp
TILE_SERVER_URL=http://localhost:8000 uv run python server.py

# ターミナル3: Admin UI起動 (ポート3000)
cd /path/to/geo-base/app
npm run dev
```

**Admin UIのみ起動する場合（本番APIを使用）:**

`.env.local` を本番API向けに設定:
```env
# 本番 API を直接叩く (dev サーバーは rewrites が効くため、API_BACKEND_URL 経由でも可)
NEXT_PUBLIC_API_URL=https://geo-base-api.fly.dev
NEXT_PUBLIC_MCP_URL=https://geo-base-mcp.fly.dev
```

```bash
npm run dev
```

### 4. 動作確認

- Admin UI: http://localhost:3000
- API (ローカル): http://localhost:8000/api/health
- API (本番): https://geo-base-api.fly.dev/api/health

## ビルドとデプロイ

```bash
# ビルド
npm run build

# 本番サーバーの起動
npm start

# リント
npm run lint
```

## ディレクトリ構成

```
app/
├── src/
│   ├── app/                          # App Router ページ
│   │   ├── page.tsx                  # ダッシュボード
│   │   ├── layout.tsx                # ルートレイアウト
│   │   ├── globals.css               # グローバルスタイル
│   │   ├── login/                    # ログイン
│   │   ├── accept-invitation/        # 招待受諾（Phase 3 / Step 3.3-A）
│   │   ├── password-reset/
│   │   │   ├── request/              # リセットメール送信
│   │   │   └── confirm/              # 新パスワード設定
│   │   ├── settings/
│   │   │   ├── profile/              # プロフィール編集
│   │   │   └── password/             # パスワード変更
│   │   ├── tilesets/                 # タイルセット管理
│   │   ├── features/                 # フィーチャー管理
│   │   ├── datasources/              # データソース
│   │   ├── teams/                    # チーム管理
│   │   └── api-keys/                 # APIキー管理
│   ├── components/
│   │   ├── ui/                       # shadcn/ui コンポーネント
│   │   └── layout/                   # レイアウトコンポーネント
│   ├── lib/
│   │   ├── api.ts                    # APIクライアント
│   │   ├── auth/                     # 認証クライアント (Phase 3 / Step 3.3-A)
│   │   │   ├── client.ts             # AuthClient: login/refresh/logout/fetch
│   │   │   ├── context.tsx           # React Context: useAuth()
│   │   │   ├── errors.ts             # エラー型
│   │   │   └── types.ts              # User / TokenPair 等
│   │   └── utils.ts                  # ユーティリティ関数
│   ├── hooks/                        # カスタムフック
│   └── types/                        # 型定義
├── public/                           # 静的ファイル
├── .env.example                      # 環境変数サンプル
├── .env.local                        # ローカル環境変数（gitignore）
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

### 認証フロー (Phase 3 / Step 3.3-A)

`app/src/lib/auth/` の `AuthClient` が `/api/auth/*` をラップします。

- **アクセストークン**: メモリ保持（`access_token`）、API リクエストの `Authorization: Bearer <token>` ヘッダで送信
- **リフレッシュトークン**: API が `geo_base_refresh` という HttpOnly Cookie で発行 / ローテーション。
  Admin UI では直接読み書きしない
- **401 応答**: `AuthClient` が自動的に `POST /api/auth/refresh` を試み、成功すれば元のリクエストをリトライ
- **永続セッション**: ページリロード時は `/api/auth/refresh` で新しい access_token を取得
- **`useAuth()` フック**: `context.tsx` から `user`, `login`, `logout`, `isAuthenticated` を提供

## 機能

### Step 3.1（現在）

- [x] Next.js プロジェクトセットアップ
- [x] Tailwind CSS + shadcn/ui セットアップ
- [x] 基本レイアウト（サイドバーナビゲーション）
- [x] ダッシュボードページ
- [x] タイルセット一覧ページ
- [x] フィーチャー一覧ページ
- [x] APIクライアント
- [x] プレースホルダーページ（ログイン、設定、データソース）

### Step 3.2

- [x] タイルセット詳細ページ
- [x] タイルセット作成/編集フォーム
- [x] MapLibre GL JS によるプレビュー
- [x] フィーチャー詳細ページ・作成/編集
- [x] GeoJSON/Shapefile アップロード

### Step 3.3-A（プラガブル認証 + チーム / ロール）

- [x] AuthClient + useAuth コンテキスト（`src/lib/auth/`）
- [x] ログイン / ログアウト / プロフィール編集 / パスワード変更
- [x] パスワードリセット（`/password-reset/request`, `/password-reset/confirm`）
- [x] 招待受諾（`/accept-invitation`）
- [x] チーム管理 / メンバー招待
- [x] APIキー管理

## 接続先API

| 環境 | API URL | MCP URL |
|-----|---------|---------|
| ローカル | http://localhost:8000 | http://localhost:8001 |
| 本番 | https://geo-base-api.fly.dev | https://geo-base-mcp.fly.dev |

## ライセンス

MIT
