# geo-base プロジェクト 引き継ぎドキュメント

**作成日**: 2025-12-12  
**最終更新**: 2025-12-14  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**本番URL (API)**: https://geo-base-puce.vercel.app/  
**本番URL (MCP)**: https://geo-base-mcp.fly.dev/  
**本番URL (Admin)**: https://geo-base-app.vercel.app/  
**APIバージョン**: 0.4.0  
**MCPバージョン**: 0.2.0  
**Admin UIバージョン**: 0.10.0

---

## 1. プロジェクト概要

### 目的
地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムの構築。MCPサーバーを通じてClaudeとの連携も可能にする。

### アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Admin UI      │     │   MCP Server    │     │   外部クライアント  │
│   (Next.js)     │     │   (FastMCP)     │     │   (MapLibre等)   │
│   ✅ Step3.15完了│     │   ✅ Fly.io稼働 │     │                   │
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

### フェーズ3: 管理画面（完了）

| Step | 内容 | 状態 |
|------|------|------|
| 3.1 | Next.jsプロジェクト設定 | ✅ 完了 |
| 3.2 | Supabase Auth連携 | ✅ 完了 |
| 3.3 | タイルセット管理UI | ✅ 完了 |
| 3.4 | フィーチャー管理UI | ✅ 完了 |
| 3.5 | 設定画面 | ✅ 完了 |
| 3.7 | GeoJSONインポート機能 | ✅ 完了 |
| 3.8 | データソース管理UI | ✅ 完了 |
| 3.9 | マップビューワー | ✅ 完了 |
| 3.10 | マップビューワー初期表示位置改善 | ✅ 完了 |
| 3.11 | DBコネクションプール枯渇対策 | ✅ 完了 |
| 3.12 | GeoJSONインポート時Bounds自動取得 | ✅ 完了 |
| 3.13 | 一括削除機能・ジオメトリエディタ | ✅ 完了 |
| 3.14 | マップキャッシュリフレッシュ修正 | ✅ 完了 |
| 3.15 | タイルセット統計・エラーハンドリング改善 | ✅ 完了 |

---

## 3. 現在のファイル構成

```
geo-base/
├── api/                          # FastAPI タイルサーバー
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── auth.py              # 認証・JWT検証【Step 1.7】
│   │   ├── cache.py             # インメモリTTLキャッシュ【Step 3.11】
│   │   ├── config.py            # 設定管理（pydantic-settings）
│   │   ├── database.py          # DB接続（サーバーレス対応）
│   │   ├── main.py              # FastAPIアプリ・エンドポイント
│   │   │                        # ※統計APIエンドポイント追加【Step 3.15】
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
├── app/                          # Next.js管理画面【Step 3.15完了】
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # ルートレイアウト
│   │   │   ├── page.tsx         # ダッシュボード（統計表示追加）【Step 3.15】
│   │   │   ├── globals.css      # グローバルスタイル
│   │   │   ├── login/
│   │   │   │   └── page.tsx     # ログインページ【Step 3.2】
│   │   │   ├── tilesets/
│   │   │   │   ├── page.tsx     # タイルセット一覧（一括削除追加）【Step 3.13】
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx # タイルセット新規作成【Step 3.3】
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx # タイルセット詳細（統計カード追加）【Step 3.15】
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx # タイルセット編集【Step 3.3】
│   │   │   ├── features/        # フィーチャー管理【Step 3.4, 3.7, 3.13】
│   │   │   │   ├── page.tsx     # フィーチャー一覧（一括削除追加）【Step 3.13】
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx # フィーチャー新規作成（ジオメトリエディタ）【Step 3.13】
│   │   │   │   ├── import/
│   │   │   │   │   └── page.tsx # GeoJSONインポート【Step 3.7】
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx # フィーチャー詳細
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx # フィーチャー編集（ジオメトリエディタ）【Step 3.13】
│   │   │   ├── datasources/     # データソース管理【Step 3.8】
│   │   │   │   ├── page.tsx     # データソース一覧
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx # データソース新規登録
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx # データソース詳細
│   │   │   └── settings/
│   │   │       └── page.tsx     # 設定画面【Step 3.5】
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── index.ts
│   │   │   │   ├── sidebar.tsx   # サイドバーナビゲーション
│   │   │   │   └── admin-layout.tsx
│   │   │   ├── tilesets/        # タイルセット関連コンポーネント【Step 3.3】
│   │   │   │   ├── tileset-form.tsx      # 作成/編集フォーム
│   │   │   │   ├── delete-tileset-dialog.tsx # 削除確認ダイアログ
│   │   │   │   └── index.ts
│   │   │   ├── features/        # フィーチャー関連コンポーネント【Step 3.4, 3.7, 3.13】
│   │   │   │   ├── feature-form.tsx      # 作成/編集フォーム
│   │   │   │   ├── delete-feature-dialog.tsx # 削除確認ダイアログ
│   │   │   │   ├── geojson-dropzone.tsx  # ドラッグ&ドロップアップロード【Step 3.7】
│   │   │   │   ├── geojson-preview.tsx   # 地図プレビュー【Step 3.7】
│   │   │   │   ├── geometry-editor.tsx   # ジオメトリエディタ【Step 3.13】
│   │   │   │   └── index.ts
│   │   │   ├── settings/        # 設定関連コンポーネント【Step 3.5】
│   │   │   │   ├── profile-form.tsx      # プロフィール編集
│   │   │   │   ├── password-form.tsx     # パスワード変更
│   │   │   │   └── index.ts
│   │   │   ├── map/             # 地図コンポーネント【Step 3.4, 3.9】
│   │   │   │   ├── map-view.tsx # MapLibre GL JS ラッパー
│   │   │   │   ├── tileset-map-preview.tsx # タイルセットプレビュー【Step 3.9】
│   │   │   │   └── index.ts
│   │   │   └── ui/              # shadcn/ui コンポーネント
│   │   │       ├── alert.tsx    # アラートコンポーネント【Step 3.8】
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── checkbox.tsx # チェックボックス【Step 3.13】
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
│   │   │   ├── api.ts           # APIクライアント
│   │   │   │                    # ※統計API追加【Step 3.15】
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
│   ├── package.json             # バージョン: 0.10.0
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── components.json          # shadcn/ui設定
│   └── README.md
├── docker/
│   ├── docker-compose.yml
│   └── postgis-init/
│       ├── 01_init.sql          # ※type制約に'pmtiles'追加【Step 3.8】
│       ├── 02_raster_schema.sql # raster_sourcesテーブル定義
│       ├── 03_pmtiles_schema.sql # pmtiles_sourcesテーブル定義
│       └── 04_rls_policies.sql  # ※ローカル開発用簡略化【Step 3.8】
├── packages/                     # 共有パッケージ（未実装）
├── scripts/
│   ├── setup.sh
│   ├── seed.sh
│   ├── seed_sample_data.fish    # サンプルデータ投入（fish shell）【Step 3.4】
│   └── seed_sample_data.py      # サンプルデータ投入（Python）【Step 3.4】
├── .github/
│   └── workflows/               # CI/CD（未実装）
├── vercel.json                  # Vercel設定（API用）
├── .gitignore
├── HANDOVER.md                  # このドキュメント
├── PROJECT_ROADMAP.md           # プロジェクトロードマップ
└── README.md                    # プロジェクト概要
```

---

## 4. 最新のステップ詳細（Step 3.13〜3.15）

### Step 3.13: 一括削除機能・ジオメトリエディタ

#### 実装内容

1. **一括削除機能**
   - タイルセット一覧：チェックボックスで複数選択、一括削除ボタン
   - フィーチャー一覧：チェックボックスで複数選択、一括削除ボタン
   - 削除確認ダイアログで選択数を表示

2. **ジオメトリエディタ**
   - フィーチャー作成/編集ページにマップ上でのジオメトリ編集機能
   - Point/LineString/Polygon対応
   - 地図クリックで座標追加、既存座標の編集・削除
   - JSON直接編集とマップ編集の切り替え

3. **UIコンポーネント追加**
   - `checkbox.tsx` - shadcn/uiチェックボックス
   - `geometry-editor.tsx` - ジオメトリエディタコンポーネント

### Step 3.14: マップキャッシュリフレッシュ修正

#### 実装内容

- フィーチャー編集後のマップ更新が正しく動作するよう修正
- `mapRefreshKey` を `Date.now()` ベースに変更（確実なキャッシュバスティング）
- 更新ボタン押下時に `isRefreshing` 状態を表示

### Step 3.15: タイルセット統計・エラーハンドリング改善

#### 実装内容

1. **システム統計API** (`GET /api/stats`)
   - タイルセット数（タイプ別、公開/非公開）
   - フィーチャー数（ジオメトリタイプ別：Point/LineString/Polygon）
   - データソース数（PMTiles/COG）
   - フィーチャー数上位タイルセット（トップ10）

2. **タイルセット統計API** (`GET /api/tilesets/{id}/stats`)
   - フィーチャー数
   - ジオメトリタイプ分布
   - バウンズ（フィーチャーから計算）
   - 最終更新日時
   - アクセス制御（非公開タイルセットはオーナーのみ）

3. **ダッシュボード機能強化**
   - フィーチャー数表示（新規統計カード）
   - ジオメトリタイプ分布表示（Point/Line/Polygon）
   - 公開/非公開タイルセット統計
   - データソース統計（PMTiles/COG数）
   - フィーチャー数上位タイルセット表示（トップ3）
   - エラー表示の改善（アイコン付きアラート）

4. **タイルセット詳細ページ機能強化**
   - フィーチャー統計カード追加（vectorタイプのみ）
   - 総フィーチャー数、Point/Line/Polygon数表示
   - 最終更新日時表示

5. **APIクライアント更新**
   - `SystemStats` 型定義追加
   - `TilesetStats` 型定義追加
   - `getSystemStats()` メソッド追加
   - `getTilesetStats(id)` メソッド追加

---

## 5. APIエンドポイント一覧

### タイル配信

| エンドポイント | メソッド | 認証 | 説明 |
|--------------|--------|-----|------|
| `/api/health` | GET | 不要 | ヘルスチェック |
| `/api/tilesets` | GET | オプション | タイルセット一覧（公開のみ or 全て） |
| `/api/tilesets/{id}` | GET | オプション | タイルセット詳細 |
| `/api/tilesets/{id}/tilejson` | GET | オプション | TileJSON取得 |
| `/api/tilesets/{id}/tiles/{z}/{x}/{y}.{format}` | GET | オプション | タイル取得 |
| `/api/stats` | GET | 不要 | システム統計【Step 3.15】 |
| `/api/tilesets/{id}/stats` | GET | オプション | タイルセット統計【Step 3.15】 |

### タイルセットCRUD

| エンドポイント | メソッド | 認証 | 説明 |
|--------------|--------|-----|------|
| `/api/tilesets` | POST | 必須 | タイルセット作成 |
| `/api/tilesets/{id}` | PUT | 必須 | タイルセット更新 |
| `/api/tilesets/{id}` | DELETE | 必須 | タイルセット削除 |

### フィーチャーCRUD

| エンドポイント | メソッド | 認証 | 説明 |
|--------------|--------|-----|------|
| `/api/features` | GET | オプション | フィーチャー一覧 |
| `/api/features/{id}` | GET | オプション | フィーチャー詳細 |
| `/api/features` | POST | 必須 | フィーチャー作成 |
| `/api/features/bulk` | POST | 必須 | フィーチャー一括作成【Step 3.7】 |
| `/api/features/{id}` | PUT | 必須 | フィーチャー更新 |
| `/api/features/{id}` | DELETE | 必須 | フィーチャー削除 |

### データソースCRUD【Step 3.8】

| エンドポイント | メソッド | 認証 | 説明 |
|--------------|--------|-----|------|
| `/api/datasources` | GET | 必須 | データソース一覧 |
| `/api/datasources/{id}` | GET | 必須 | データソース詳細 |
| `/api/datasources` | POST | 必須 | データソース作成 |
| `/api/datasources/{id}` | PUT | 必須 | データソース更新 |
| `/api/datasources/{id}` | DELETE | 必須 | データソース削除 |
| `/api/datasources/{id}/test` | POST | 必須 | データソース接続テスト |

---

## 6. 環境変数

### API（api/.env）

```bash
# データベース
DATABASE_URL=postgresql://user:pass@host:5432/db

# 認証（Supabase）
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_JWT_SECRET=xxx

# 環境
ENVIRONMENT=development  # development | production
```

### Admin UI（app/.env.local）

```bash
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
```

### MCP Server（mcp/.env）

```bash
# API
GEO_BASE_API_URL=http://localhost:8000
GEO_BASE_AUTH_TOKEN=xxx  # オプション

# サーバー設定
MCP_TRANSPORT=stdio  # stdio | sse
```

---

## 7. 今後の課題

### 高優先度

#### 本番デプロイ

**対象**:
- API（統計エンドポイント追加）
- Admin UI（統計表示、一括削除、ジオメトリエディタ）

**手順**:
```bash
# develop → main へマージ後、自動デプロイ
git checkout main
git merge develop
git push origin main
```

**注意点**:
- Supabaseの本番DBに`pmtiles_sources`と`raster_sources`テーブルが必要
- 本番のRLSポリシーは`04_rls_policies.sql.supabase`を使用

### 中優先度

#### Toast通知システム統合

**目的**: CRUD操作の成功/失敗をユーザーにフィードバック

**実装方針**:
1. Toast通知コンポーネントは作成済み（`app/src/components/ui/toast.tsx`）
2. 各ページのCRUD操作にToast呼び出しを追加
3. 成功時は緑色、エラー時は赤色で表示

**優先度**: 中

#### ドキュメント整備

**目的**: 開発者向けドキュメントの充実

**実装方針**:
1. API仕様書（OpenAPI/Swagger）の整備
2. MCPサーバーのツール一覧ドキュメント
3. ローカル開発環境セットアップガイドの更新

**優先度**: 中

### 低優先度

#### 権限管理の高度化

**目的**: チーム利用時の権限管理

**実装方針**:
1. ロールベースアクセス制御（RBAC）
2. タイルセット単位の共有設定
3. 組織機能の追加

**優先度**: 低

#### パフォーマンス最適化

**目的**: 大量データ時のレスポンス改善

**実装方針**:
1. タイルキャッシュのCDN連携
2. フィーチャー検索のインデックス最適化
3. ページネーションの改善

**優先度**: 低

### 完了した課題

#### ~~タイルセット統計・分析機能~~ ✅ 完了（Step 3.15）

- システム統計API追加
- タイルセット統計API追加
- ダッシュボードに統計表示
- タイルセット詳細に統計カード追加

#### ~~一括削除機能~~ ✅ 完了（Step 3.13）

- タイルセット一覧での一括削除
- フィーチャー一覧での一括削除

#### ~~ジオメトリエディタ~~ ✅ 完了（Step 3.13）

- マップ上でのジオメトリ編集
- Point/LineString/Polygon対応

#### ~~マップキャッシュリフレッシュ~~ ✅ 完了（Step 3.14）

- フィーチャー編集後のマップ更新修正

---

## 8. 既知の問題

### 1. DB接続プール枯渇

**症状**: 多数のタイルリクエストで `connection pool exhausted` エラー

**暫定対応**: APIサーバー再起動

**恒久対応案**:
- 接続プールサイズの調整（`database.py`の`minconn`/`maxconn`）
- コネクションのタイムアウト設定
- Vercel Serverless環境での接続管理最適化

### 2. Radix UI + Tailwind CSS v4 互換性

**症状**: Select, Dialog等のポータルコンポーネントが正常に表示されない場合がある

**暫定対応**: ネイティブHTML要素を使用（フィーチャー一覧のセレクト）

**恒久対応案**:
- Tailwind CSS v3へのダウングレード検討
- shadcn/ui コンポーネントのカスタマイズ

### 3. タイルセットタイプの制約

| タイプ | フィーチャー編集 | データソース |
|--------|----------------|------------|
| vector | ✅ 可能 | ❌ 不要（PostGIS） |
| pmtiles | ❌ 不可 | ✅ 必須（PMTilesファイル） |
| raster | ❌ 不可 | ✅ 必須（COGファイル） |

### 4. Next.js 16 Middleware警告

**症状**: ビルド時に `middleware` ファイル規約が非推奨との警告が表示される

**対応**: 次回メジャーアップデート時に `proxy` への移行を検討

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
| Admin UI Map | MapLibre GL JS | 4.7.x | 地図表示【Step 3.4, 3.7】 |
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
| PMTiles | aiopm