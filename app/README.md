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
│   ├── app/                    # App Router ページ
│   │   ├── page.tsx            # ダッシュボード
│   │   ├── layout.tsx          # ルートレイアウト
│   │   ├── globals.css         # グローバルスタイル
│   │   ├── login/              # ログインページ
│   │   ├── tilesets/           # タイルセット管理
│   │   ├── features/           # フィーチャー管理
│   │   ├── datasources/        # データソース
│   │   └── settings/           # 設定
│   ├── components/
│   │   ├── ui/                 # shadcn/ui コンポーネント
│   │   └── layout/             # レイアウトコンポーネント
│   ├── lib/
│   │   ├── api.ts              # APIクライアント
│   │   └── utils.ts            # ユーティリティ関数
│   ├── hooks/                  # カスタムフック
│   └── types/                  # 型定義
├── public/                     # 静的ファイル
├── .env.example                # 環境変数サンプル
├── .env.local                  # ローカル環境変数（gitignore）
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

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

### Step 3.2（予定）

- [ ] Supabase Auth 連携
- [ ] ログイン/ログアウト機能
- [ ] セッション管理
- [ ] 認証ミドルウェア

### Step 3.3（予定）

- [ ] タイルセット詳細ページ
- [ ] タイルセット作成/編集フォーム
- [ ] MapLibre GL JS によるプレビュー

### Step 3.4（予定）

- [ ] フィーチャー詳細ページ
- [ ] フィーチャー作成/編集
- [ ] GeoJSON/Shapefile アップロード

## 接続先API

| 環境 | API URL | MCP URL |
|-----|---------|---------|
| ローカル | http://localhost:8000 | http://localhost:8001 |
| 本番 | https://geo-base-api.fly.dev | https://geo-base-mcp.fly.dev |

## ライセンス

MIT
