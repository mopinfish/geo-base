# geo-base プロジェクト 引き継ぎドキュメント

**作成日**: 2025-12-12  
**最終更新**: 2025-12-13  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**本番URL (API)**: https://geo-base-puce.vercel.app/  
**本番URL (MCP)**: https://geo-base-mcp.fly.dev/  
**本番URL (Admin)**: https://geo-base-app.vercel.app/  
**APIバージョン**: 0.3.0  
**MCPバージョン**: 0.2.0  
**Admin UIバージョン**: 0.3.0

---

## 1. プロジェクト概要

### 目的
地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムの構築。MCPサーバーを通じてClaudeとの連携も可能にする。

### アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Admin UI      │     │   MCP Server    │     │   外部クライアント  │
│   (Next.js)     │     │   (FastMCP)     │     │   (MapLibre等)   │
│   ✅ Step3.3完了│     │   ✅ Fly.io稼働 │     │                   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Tile Server API     │
                    │   (FastAPI on Vercel)   │
                    │   ✅ 本番稼働中         │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌────────▼────────┐  ┌─────────▼─────────┐
│ PostgreSQL+PostGIS│  │ Supabase Storage │  │   External COG    │
│    (Supabase)     │  │   (PMTiles)      │  │   (S3, HTTP)      │
└───────────────────┘  └──────────────────┘  └───────────────────┘
```

---

## 2. 完了した作業

### フェーズ1: タイルサーバーAPI（完了）

| Step | 内容 | 状態 |
|------|------|------|
| 1.1 | プロジェクト初期設定 | ✅ 完了 |
| 1.2 | FastAPIタイルサーバー構築 | ✅ 完了 |
| 1.3 | 動的タイル生成機能の充実 | ✅ 完了 |
| 1.4 | Vercelデプロイ | ✅ 完了 |
| 1.5 | ラスタタイル対応（COG/GeoTIFF） | ⚠️ 部分完了（Vercelでは動作不可） |
| 1.6 | PMTiles対応 | ✅ 完了 |
| 1.7 | 認証機能（Supabase Auth） | ✅ 完了 |

### フェーズ2: MCPサーバー（完了）

| Step | 内容 | 状態 |
|------|------|------|
| 2.1 | FastMCPサーバー基盤構築 | ✅ 完了 |
| 2.2 | ローカル動作確認・テスト | ✅ 完了 |
| 2.3 | Fly.ioデプロイ | ✅ 完了 |
| 2.4 | Claude Desktop連携確認 | ✅ 完了 |
| 2.4-A | ジオコーディングツール追加 | ✅ 完了 |
| 2.4-B | CRUDツール追加 | ✅ 完了 |

### フェーズ3: 管理画面（進行中）

| Step | 内容 | 状態 |
|------|------|------|
| 3.1 | Next.jsプロジェクト設定 | ✅ 完了 |
| 3.2 | Supabase Auth連携 | ✅ 完了 |
| 3.3 | タイルセット管理UI | ✅ 完了 |
| 3.4 | フィーチャー管理UI | 📋 未着手 |

---

## 3. 現在のファイル構成

```
geo-base/
├── api/                          # FastAPI タイルサーバー
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── auth.py              # 認証・JWT検証【Step 1.7】
│   │   ├── config.py            # 設定管理（pydantic-settings）
│   │   ├── database.py          # DB接続（サーバーレス対応）
│   │   ├── main.py              # FastAPIアプリ・エンドポイント
│   │   │                        # ※CRUDエンドポイント追加済み【Step 2.4-B】
│   │   ├── pmtiles.py           # PMTilesユーティリティ【Step 1.6】
│   │   ├── raster_tiles.py      # ラスタータイル生成ユーティリティ
│   │   └── tiles.py             # ベクタータイル生成ユーティリティ
│   ├── data/                    # MBTilesファイル格納（ローカル用）
│   ├── index.py                 # Vercelエントリーポイント
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── .env.example
│   └── .python-version
├── mcp/                          # MCPサーバー【Step 2完了】
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tilesets.py          # タイルセット関連ツール
│   │   ├── features.py          # フィーチャー関連ツール
│   │   ├── geocoding.py         # ジオコーディングツール【Step 2.4-A】
│   │   └── crud.py              # CRUD操作ツール【Step 2.4-B】
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_tools.py        # タイルセット・フィーチャーテスト
│   │   ├── test_geocoding.py    # ジオコーディングテスト【Step 2.4-A】
│   │   ├── test_crud.py         # CRUDテスト【Step 2.4-B】
│   │   └── live_test.py         # ライブテストスクリプト
│   ├── server.py                # FastMCPサーバー本体（16ツール）
│   ├── config.py                # 設定管理
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile               # Fly.io用【Step 2.3】
│   ├── fly.toml                 # Fly.io設定【Step 2.3】
│   ├── .dockerignore            # Docker除外設定【Step 2.3】
│   ├── README.md                # 日本語ドキュメント
│   ├── .env.example
│   ├── .python-version
│   └── claude_desktop_config.example.json
├── app/                          # Next.js管理画面【Step 3.3完了】
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # ルートレイアウト
│   │   │   ├── page.tsx         # ダッシュボード
│   │   │   ├── globals.css      # グローバルスタイル
│   │   │   ├── login/
│   │   │   │   └── page.tsx     # ログインページ【Step 3.2】
│   │   │   ├── tilesets/
│   │   │   │   ├── page.tsx     # タイルセット一覧【Step 3.3】
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx # タイルセット新規作成【Step 3.3】
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx # タイルセット詳細【Step 3.3】
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx # タイルセット編集【Step 3.3】
│   │   │   ├── features/
│   │   │   │   └── page.tsx     # フィーチャー一覧（プレースホルダー）
│   │   │   ├── datasources/
│   │   │   │   └── page.tsx     # データソース（プレースホルダー）
│   │   │   └── settings/
│   │   │       └── page.tsx     # 設定（プレースホルダー）
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── index.ts
│   │   │   │   ├── sidebar.tsx   # サイドバーナビゲーション
│   │   │   │   └── admin-layout.tsx
│   │   │   ├── tilesets/        # タイルセット関連コンポーネント【Step 3.3】
│   │   │   │   ├── tileset-form.tsx      # 作成/編集フォーム
│   │   │   │   └── delete-tileset-dialog.tsx # 削除確認ダイアログ
│   │   │   └── ui/              # shadcn/ui コンポーネント
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── input.tsx
│   │   │       ├── label.tsx
│   │   │       ├── table.tsx
│   │   │       ├── select.tsx
│   │   │       ├── dialog.tsx
│   │   │       ├── dropdown-menu.tsx
│   │   │       ├── badge.tsx
│   │   │       ├── switch.tsx
│   │   │       ├── textarea.tsx
│   │   │       ├── alert-dialog.tsx
│   │   │       └── separator.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # APIクライアント【Step 3.3で改善】
│   │   │   ├── utils.ts         # ユーティリティ（cn関数）
│   │   │   └── supabase/        # Supabase クライアント【Step 3.2】
│   │   │       ├── client.ts    # ブラウザ用クライアント
│   │   │       ├── server.ts    # サーバー用クライアント
│   │   │       └── middleware.ts # セッション更新
│   │   ├── hooks/
│   │   │   ├── index.ts
│   │   │   └── use-api.ts       # 認証付きAPIフック【Step 3.3】
│   │   └── types/
│   │       └── index.ts         # 型定義
│   ├── middleware.ts            # Next.js認証ミドルウェア【Step 3.2】
│   ├── public/                  # 静的ファイル
│   ├── .env.example             # 環境変数サンプル
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── components.json          # shadcn/ui設定
│   └── README.md
├── docker/
│   ├── docker-compose.yml
│   └── postgis-init/
│       ├── 01_init.sql
│       ├── 02_raster_schema.sql
│       ├── 03_pmtiles_schema.sql
│       └── 04_rls_policies.sql
├── packages/                     # 共有パッケージ（未実装）
├── scripts/
│   ├── setup.sh
│   └── seed.sh
├── vercel.json                   # API用（既存のまま）
├── DEPLOY.md
├── TESTING.md                    # 動作確認手順【Step 2.4-B】
├── LOCAL_DEVELOPMENT.md          # ローカル開発環境ガイド【Step 3.1】
├── HANDOVER.md
└── README.md
```

---

## 4. ローカル開発環境

### ポート割り当て

| コンポーネント | ポート | ディレクトリ | 説明 |
|--------------|--------|-------------|------|
| **Admin UI** | 3000 | `/app` | Next.js 管理画面 |
| **API** | 8000 | `/api` | FastAPI タイルサーバー |
| **MCP Server** | 8001 | `/mcp` | Claude Desktop連携（SSEモード） |

### 起動方法（3つのターミナル）

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

### 環境変数

#### Admin UI (`/app/.env.local`)

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-anon-key

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# MCP（オプション）
NEXT_PUBLIC_MCP_URL=http://localhost:8001
```

#### Vercel環境変数（Admin UI）

| 変数名 | 説明 |
|--------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase プロジェクトURL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |
| `NEXT_PUBLIC_API_URL` | API URL（`https://geo-base-puce.vercel.app`） |
| `NEXT_PUBLIC_MCP_URL` | MCP URL（`https://geo-base-mcp.fly.dev`） |

---

## 5. Step 3.3 完了内容詳細

### タイルセット管理UI機能

| 機能 | パス | 説明 |
|------|------|------|
| 一覧表示 | `/tilesets` | フィルター（タイプ、公開状態）、検索機能付き |
| 詳細表示 | `/tilesets/[id]` | メタデータ、APIエンドポイントURL表示 |
| 新規作成 | `/tilesets/new` | フォームバリデーション付き |
| 編集 | `/tilesets/[id]/edit` | 既存データのプリフィル |
| 削除 | 詳細ページから | 確認ダイアログ付き |

### 修正したバグと対応

| 問題 | 原因 | 対応 |
|------|------|------|
| タイルセット一覧が0件 | APIレスポンスが `{tilesets: [], count: N}` 形式 | オブジェクト形式に対応 |
| 削除時にJSONエラー | DELETE APIが204 No Content | 空レスポンス対応 |
| 編集画面でエラー | bounds/centerが文字列形式 | `parseCoordinates`関数で両形式対応 |
| 詳細ページでエラー | 同上 | 同上 |
| 認証タイミング問題 | トークン設定前にAPI呼び出し | `useApi`に`isReady`状態追加 |

### APIクライアント改善点

```typescript
// app/src/lib/api.ts

// 1. 空レスポンス対応
if (response.status === 204 || contentLength === '0') {
  return null as T;
}

// 2. レスポンス形式の自動判定
const text = await response.text();
if (!text) return null as T;
return JSON.parse(text) as T;
```

```typescript
// app/src/hooks/use-api.ts

// isReady状態でトークン設定完了を管理
export function useApi() {
  const [isReady, setIsReady] = useState(false);
  // ...
  return { api, isReady };
}
```

---

## 6. タイルビューア設定

### MVTタイルのレイヤー名

geo-baseのフィーチャーベースMVTタイルのレイヤー名は **`features`** です。

```javascript
// tile-viewer.html での正しい設定
{
  id: 'points',
  type: 'circle',
  source: 'geobase',
  'source-layer': 'features',  // ← 'landmarks' や 'default' ではない
  paint: {
    'circle-radius': 12,
    'circle-color': '#e74c3c',
    'circle-stroke-width': 2,
    'circle-stroke-color': '#fff'
  }
}
```

### サンプルHTMLビューア

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>geo-base タイルビューア</title>
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    body { margin: 0; }
    #map { width: 100%; height: 100vh; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    // ★ここを変更★
    const TILESET_ID = 'your-tileset-id';
    const API_URL = 'http://localhost:8000';  // or 'https://geo-base-puce.vercel.app'

    const map = new maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256
          },
          geobase: {
            type: 'vector',
            tiles: [`${API_URL}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${TILESET_ID}`]
          }
        },
        layers: [
          { id: 'osm', type: 'raster', source: 'osm' },
          {
            id: 'points',
            type: 'circle',
            source: 'geobase',
            'source-layer': 'features',  // ← 重要
            paint: {
              'circle-radius': 12,
              'circle-color': '#e74c3c',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff'
            }
          }
        ]
      },
      center: [139.7671, 35.6812],
      zoom: 12
    });
    map.addControl(new maplibregl.NavigationControl());
  </script>
</body>
</html>
```

---

## 7. 今後の課題と実装方針

### Step 3.4: フィーチャー管理UI

#### 実装内容
- フィーチャー一覧ページ（タイルセット別フィルタリング）
- フィーチャー詳細ページ
- フィーチャー作成（座標手動入力、地図クリック）
- フィーチャー編集（属性、ジオメトリ）
- フィーチャー削除
- MapLibre GL JSによる地図上での可視化
- GeoJSONインポート機能（オプション）

#### 必要なパッケージ

```bash
npm install maplibre-gl
```

#### ファイル構成（追加予定）

```
app/src/
├── app/
│   └── features/
│       ├── page.tsx           # フィーチャー一覧
│       ├── new/
│       │   └── page.tsx       # フィーチャー新規作成
│       └── [id]/
│           ├── page.tsx       # フィーチャー詳細
│           └── edit/
│               └── page.tsx   # フィーチャー編集
├── components/
│   ├── features/
│   │   ├── feature-form.tsx   # 作成/編集フォーム
│   │   ├── feature-map.tsx    # 地図コンポーネント
│   │   └── delete-feature-dialog.tsx
│   └── map/
│       ├── map-view.tsx       # MapLibre GL JS ラッパー
│       └── map-controls.tsx   # 地図コントロール
```

#### 実装のポイント

1. **地図コンポーネント**: MapLibre GL JSをReactで使う場合、`useRef`と`useEffect`でインスタンス管理
2. **座標入力**: フォームでの手動入力と地図クリックの両方をサポート
3. **GeoJSON表示**: フィーチャーのジオメトリを地図上にハイライト表示
4. **タイルセット連携**: タイルセットIDでフィルタリング

### 既知の問題

#### DB接続プール枯渇

**症状**: 多数のタイルリクエストで `connection pool exhausted` エラー

**暫定対応**: APIサーバー再起動

**恒久対応案**:
- 接続プールサイズの調整（`database.py`の`minconn`/`maxconn`）
- コネクションのタイムアウト設定
- Vercel Serverless環境での接続管理最適化

---

## 8. MCPサーバー詳細【Phase 2完了】

### 本番環境

| 項目 | 値 |
|------|-----|
| ホスティング | Fly.io |
| URL | https://geo-base-mcp.fly.dev |
| SSEエンドポイント | https://geo-base-mcp.fly.dev/sse |
| リージョン | nrt (東京) |
| トランスポート | SSE |

### 実装されたツール（16ツール）

#### タイルセットツール
| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `tool_list_tilesets` | タイルセット一覧取得 | `type?`, `is_public?` |
| `tool_get_tileset` | タイルセット詳細取得 | `tileset_id` |
| `tool_get_tileset_tilejson` | TileJSON取得 | `tileset_id` |

#### フィーチャーツール
| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `tool_search_features` | フィーチャー検索 | `bbox?`, `layer?`, `filter?`, `limit?`, `tileset_id?` |
| `tool_get_feature` | フィーチャー詳細取得 | `feature_id` |

#### ジオコーディングツール【Step 2.4-A】
| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `tool_geocode` | 住所→座標変換 | `query`, `limit?`, `country_codes?`, `language?` |
| `tool_reverse_geocode` | 座標→住所変換 | `latitude`, `longitude`, `zoom?`, `language?` |

#### CRUDツール【Step 2.4-B】（認証必須）
| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `tool_create_tileset` | タイルセット作成 | `name`, `type`, `format`, `description?`, ... |
| `tool_update_tileset` | タイルセット更新 | `tileset_id`, `name?`, `description?`, ... |
| `tool_delete_tileset` | タイルセット削除 | `tileset_id` |
| `tool_create_feature` | フィーチャー作成 | `tileset_id`, `geometry`, `properties?`, `layer_name?` |
| `tool_update_feature` | フィーチャー更新 | `feature_id`, `geometry?`, `properties?`, `layer_name?` |
| `tool_delete_feature` | フィーチャー削除 | `feature_id` |

#### ユーティリティツール
| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `tool_get_tile_url` | タイルURL生成 | `tileset_id`, `z`, `x`, `y`, `format?` |
| `tool_health_check` | ヘルスチェック | なし |
| `tool_get_server_info` | サーバー情報取得 | なし |

### Claude Desktop設定

#### ローカル接続
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "geo-base-local": {
      "command": "/Users/otsuka/.local/bin/uv",
      "args": [
        "--directory",
        "/path/to/geo-base/mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "TILE_SERVER_URL": "https://geo-base-puce.vercel.app"
      }
    }
  }
}
```

#### リモート接続（Fly.io）

```json
{
  "mcpServers": {
    "geo-base-remote": {
      "command": "/Users/otsuka/.local/bin/uvx",
      "args": [
        "mcp-proxy",
        "https://geo-base-mcp.fly.dev/sse",
        "--transport=sse"
      ]
    }
  }
}
```

---

## 9. 技術スタック

| レイヤー | 技術 | バージョン | 備考 |
|---------|------|-----------|------|
| Admin UI Framework | Next.js | 16.x | App Router |
| Admin UI Language | TypeScript | 5.x | |
| Admin UI Styling | Tailwind CSS | 4.x | |
| Admin UI Components | shadcn/ui | - | 手動セットアップ |
| Admin UI Icons | Lucide React | 0.560.x | |
| Admin UI Auth | @supabase/ssr | 0.5.x | サーバーサイド認証 |
| API Framework | FastAPI | 0.115.x | |
| Database | PostgreSQL + PostGIS | 16 + 3.4 | |
| Database Hosting | Supabase | - | Auth, Storage含む |
| API Hosting | Vercel Serverless | Python 3.12 | |
| MCP Framework | FastMCP | 2.14.0 | |
| MCP Hosting | Fly.io | - | SSEトランスポート |
| MCP Proxy | mcp-proxy | 0.10.0 | リモート接続用 |
| Package Manager (Python) | uv | latest | |
| Package Manager (Node) | npm | - | |
| Vector Tiles | PostGIS ST_AsMVT | - | |
| PMTiles | aiopmtiles | 0.1.0 | ✅ Vercelで動作 |
| Raster Tiles | rio-tiler | 7.0+ | ⚠️ Vercelでは動作不可 |
| Authentication | Supabase Auth + PyJWT | - | ✅ JWT検証実装済み |
| Geocoding | Nominatim API | - | OpenStreetMap |
| Tile Format | MVT (pbf), PNG, WebP | - | |
| Map Visualization | MapLibre GL JS | 4.7.x | タイルビューア |

---

## 10. APIエンドポイント一覧

### 認証エンドポイント

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/auth/me` | 必須 | 認証ユーザー情報取得 |
| GET | `/api/auth/status` | 不要 | 認証状態確認 |

### ヘルスチェック

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/health/db` | DB接続チェック |

### タイルセット管理

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/tilesets` | 不要※ | タイルセット一覧 |
| POST | `/api/tilesets` | 必須 | タイルセット作成 |
| GET | `/api/tilesets/{id}` | 条件付き | タイルセット詳細 |
| PATCH | `/api/tilesets/{id}` | 必須 | タイルセット更新 |
| DELETE | `/api/tilesets/{id}` | 必須 | タイルセット削除 |
| GET | `/api/tilesets/{id}/tilejson.json` | 条件付き | TileJSON |

### フィーチャー管理

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/features` | 不要※ | フィーチャー検索 |
| POST | `/api/features` | 必須 | フィーチャー作成 |
| GET | `/api/features/{id}` | 条件付き | フィーチャー詳細 |
| PATCH | `/api/features/{id}` | 必須 | フィーチャー更新 |
| DELETE | `/api/features/{id}` | 必須 | フィーチャー削除 |

### タイル配信

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/tiles/features/{z}/{x}/{y}.pbf` | 条件付き | フィーチャーMVT |
| GET | `/api/tiles/dynamic/{layer}/{z}/{x}/{y}.pbf` | 不要 | 動的MVT |
| GET | `/api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.{format}` | 条件付き | PMTilesタイル |
| GET | `/api/tiles/pmtiles/{tileset_id}/tilejson.json` | 条件付き | TileJSON |

---

## 11. 本番環境URL一覧

| サービス | URL | プラットフォーム | 状態 |
|---------|-----|----------------|------|
| Admin UI | https://geo-base-app.vercel.app | Vercel | ✅ 稼働中 |
| API | https://geo-base-puce.vercel.app | Vercel | ✅ 稼働中 |
| MCP Server | https://geo-base-mcp.fly.dev | Fly.io | ✅ 稼働中 |

---

## 12. 参照資料

### プロジェクト内ドキュメント
- `/mnt/project/geolocation-tech-source.txt` - タイルサーバー実装のサンプルコード
- `/mnt/project/PROJECT_ROADMAP.md` - プロジェクトロードマップ
- `/mnt/project/geo-base.txt` - 最新ソースコード
- `TESTING.md` - 動作確認手順
- `LOCAL_DEVELOPMENT.md` - ローカル開発環境ガイド

### 外部ドキュメント
- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Supabase Auth (SSR)](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [PostGIS MVT Functions](https://postgis.net/docs/ST_AsMVT.html)
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/)

---

## 13. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-12 | 0.1.0 | 初版作成（Step 1.1〜1.4完了） |
| 2025-12-12 | 0.2.0 | ラスタタイル対応（Step 1.5）、PMTiles対応（Step 1.6）追加 |
| 2025-12-12 | 0.3.0 | 認証機能（Step 1.7）追加 |
| 2025-12-12 | 0.4.0 | MCPサーバー基盤構築（Step 2.1）、テスト追加（Step 2.2） |
| 2025-12-12 | 0.5.0 | Fly.ioデプロイ（Step 2.3）、Claude Desktop連携確認（Step 2.4） |
| 2025-12-12 | 0.6.0 | ジオコーディングツール追加（Step 2.4-A） |
| 2025-12-12 | 0.7.0 | CRUDツール追加（Step 2.4-B）、Phase 2完了 |
| 2025-12-13 | 0.8.0 | Next.js Admin UI基盤構築（Step 3.1完了） |
| 2025-12-13 | 0.9.0 | Supabase Auth連携（Step 3.2完了） |
| 2025-12-13 | 1.0.0 | タイルセット管理UI（Step 3.3完了）、バグ修正、タイル表示確認 |

---

*このドキュメントは2025-12-13時点の情報です。APIバージョン: 0.3.0 / MCPバージョン: 0.2.0 / Admin UIバージョン: 0.3.0*
