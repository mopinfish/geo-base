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
**Admin UIバージョン**: 0.8.0

---

## 1. プロジェクト概要

### 目的
地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムの構築。MCPサーバーを通じてClaudeとの連携も可能にする。

### アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Admin UI      │     │   MCP Server    │     │   外部クライアント  │
│   (Next.js)     │     │   (FastMCP)     │     │   (MapLibre等)   │
│   ✅ Step3.8完了│     │   ✅ Fly.io稼働 │     │                   │
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
| 3.4 | フィーチャー管理UI | ✅ 完了 |
| 3.5 | 設定画面 | ✅ 完了 |
| 3.7 | GeoJSONインポート機能 | ✅ 完了 |
| 3.8 | データソース管理UI | ✅ 完了 |
| 3.9 | マップビューワー | ✅ 完了 |

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
│   │   │                        # ※データソースAPIエンドポイント追加【Step 3.8】
│   │   ├── pmtiles.py           # PMTilesユーティリティ【Step 1.6】
│   │   │                        # ※aiopmtiles Enum対応修正【Step 3.8】
│   │   ├── raster_tiles.py      # ラスタータイル生成ユーティリティ
│   │   │                        # ※rio-tiler Info属性対応修正【Step 3.8】
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
├── app/                          # Next.js管理画面【Step 3.8完了】
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # ルートレイアウト
│   │   │   ├── page.tsx         # ダッシュボード（タイルセット数表示修正済み）
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
│   │   │   ├── features/        # フィーチャー管理【Step 3.4, 3.7】
│   │   │   │   ├── page.tsx     # フィーチャー一覧（インポートボタン追加）
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx # フィーチャー新規作成
│   │   │   │   ├── import/
│   │   │   │   │   └── page.tsx # GeoJSONインポート【Step 3.7】
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx # フィーチャー詳細
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx # フィーチャー編集
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
│   │   │   ├── features/        # フィーチャー関連コンポーネント【Step 3.4, 3.7】
│   │   │   │   ├── feature-form.tsx      # 作成/編集フォーム
│   │   │   │   ├── delete-feature-dialog.tsx # 削除確認ダイアログ
│   │   │   │   ├── geojson-dropzone.tsx  # ドラッグ&ドロップアップロード【Step 3.7】
│   │   │   │   ├── geojson-preview.tsx   # 地図プレビュー【Step 3.7】
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
│   │   │   │                    # ※Datasource型・API追加【Step 3.8】
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
│   ├── package.json             # バージョン: 0.7.0
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
├── vercel.json                   # API用（既存のまま）
├── DEPLOY.md
├── TESTING.md                    # 動作確認手順【Step 2.4-B】
├── LOCAL_DEVELOPMENT.md          # ローカル開発環境ガイド【Step 3.1】
├── HANDOVER.md                   # 本ドキュメント
├── PROJECT_ROADMAP.md            # プロジェクトロードマップ
└── README.md
```

---

## 4. データベーススキーマ

### テーブル一覧

| テーブル名 | 説明 |
|-----------|------|
| tilesets | タイルセットのメタデータ |
| features | ベクタフィーチャーデータ（PostGIS geometry） |
| tile_files | 静的タイルファイルの参照情報 |
| pmtiles_sources | PMTilesファイルのソース情報【Step 3.8】 |
| raster_sources | COGファイルのソース情報【Step 3.8】 |

### pmtiles_sources テーブル【Step 3.8】

```sql
CREATE TABLE pmtiles_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL UNIQUE REFERENCES tilesets(id) ON DELETE CASCADE,
    pmtiles_url TEXT NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'supabase',  -- 'supabase', 's3', 'http'
    tile_type VARCHAR(20),        -- 'vector', 'raster', 'unknown'
    tile_compression VARCHAR(20), -- 'gzip', 'zstd', 'br', 'none'
    min_zoom INTEGER,
    max_zoom INTEGER,
    bounds JSONB,                 -- [west, south, east, north]
    center JSONB,                 -- [lng, lat, zoom]
    layers JSONB DEFAULT '[]',    -- Vector layer info for MVT
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### raster_sources テーブル【Step 3.8】

```sql
CREATE TABLE raster_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL UNIQUE REFERENCES tilesets(id) ON DELETE CASCADE,
    cog_url TEXT NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'http',
    band_count INTEGER,
    band_descriptions JSONB DEFAULT '[]',
    statistics JSONB DEFAULT '{}',
    native_crs VARCHAR(50),
    native_resolution FLOAT,
    recommended_min_zoom INTEGER,
    recommended_max_zoom INTEGER,
    bounds JSONB,
    center JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 制約

- 1つのタイルセットには最大1つのデータソース（PMTiles OR COG、両方は不可）
- `tileset_id`にUNIQUE制約

---

## 5. Step 3.8 データソース管理UI 詳細

### 実装内容

| サブステップ | 内容 | ファイル |
|-------------|------|---------|
| 3.8.1 | API拡張（データソースエンドポイント） | `api/lib/main.py` |
| 3.8.2 | データソース一覧UI | `app/src/app/datasources/page.tsx` |
| 3.8.3 | データソース新規登録フォーム | `app/src/app/datasources/new/page.tsx` |
| 3.8.4 | データソース詳細ページ | `app/src/app/datasources/[id]/page.tsx` |
| 3.8.5 | 接続テスト機能 | 各ページに統合 |

### APIエンドポイント（データソース）

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/datasources` | 不要※ | データソース一覧 |
| GET | `/api/datasources/{id}` | 条件付き | データソース詳細 |
| POST | `/api/datasources` | 必須 | データソース作成 |
| DELETE | `/api/datasources/{id}` | 必須 | データソース削除 |
| POST | `/api/datasources/{id}/test` | 必須 | 接続テスト |

※ 公開タイルセットのデータソースは認証不要で取得可能

### 機能

1. **一覧表示**: PMTiles/COGを統合表示、タイプ別フィルタリング
2. **新規登録**: タイプ選択 → タイルセット選択 → URL入力 → ストレージプロバイダ自動検出
3. **詳細表示**: メタデータ、関連タイルセットへのリンク、接続テスト
4. **接続テスト**: PMTilesはメタデータ取得、COGは情報取得で確認

### 修正されたバグ

| ファイル | 問題 | 修正内容 |
|---------|------|---------|
| `api/lib/pmtiles.py` | `reader.header()`メソッド呼び出しエラー | `reader.header`プロパティに変更、Enum値の`.value`取得 |
| `api/lib/raster_tiles.py` | `info.minzoom`属性がない | `getattr()`で安全にアクセス、`cog.minzoom`へのフォールバック |
| `docker/postgis-init/01_init.sql` | `type`制約に`'pmtiles'`がない | 制約に追加 |
| `docker/postgis-init/04_rls_policies.sql` | `authenticated`ロールがローカルにない | ローカル開発用に全許可ポリシーに変更 |

---

## 6. Step 3.9 マップビューワー 詳細

### 実装内容

| サブステップ | 内容 | ファイル |
|-------------|------|---------|
| 3.9.1 | TilesetMapPreviewコンポーネント | `app/src/components/map/tileset-map-preview.tsx` |
| 3.9.2 | mapエクスポート更新 | `app/src/components/map/index.ts` |
| 3.9.3 | タイルセット詳細ページに統合 | `app/src/app/tilesets/[id]/page.tsx` |

### TilesetMapPreviewコンポーネント機能

1. **タイルセットタイプ別表示**
   - vector: PostGISベースのMVTタイル表示
   - pmtiles: PMTilesファイルからのタイル表示
   - raster: COGベースのラスタータイル表示

2. **自動設定**
   - TileJSONまたはタイルセット情報から中心座標・ズームを自動計算
   - boundsから中心を計算するフォールバック

3. **レイヤースタイル**
   - ポリゴン: 塗りつぶし + 境界線
   - ライン: 線描画
   - ポイント: サークル + ストローク

4. **インタラクション**
   - ポイントクリックでプロパティ表示（ポップアップ）
   - 「範囲にフィット」ボタン
   - 表示/非表示トグル

### Props

| プロパティ | 型 | 説明 |
|-----------|---|------|
| tileset | Tileset | タイルセット情報（必須） |
| tileJSON | TileJSON \| null | TileJSON（オプション） |
| height | string | 地図の高さ（デフォルト: "400px"） |
| fillColor | string | ポリゴン塗りつぶし色 |
| lineColor | string | 線の色 |
| pointColor | string | ポイントの色 |
| hideBaseMap | boolean | ベースマップを非表示にするか |

### 動作確認結果（2025-12-14）

| タイルタイプ | 動作確認 | 備考 |
|-------------|----------|------|
| PMTiles | ✅ 成功 | フィレンツェ地域のサンプルデータで表示確認 |
| COG (ラスター) | ✅ 成功 | 北海道南部（Sentinel-2 Tile 54TWN）で表示確認 |
| Vector (PostGIS) | ✅ 成功 | 既存のPostGISベースMVT表示確認済み |

### 注意事項

1. **タイルの範囲**: PMTiles/COGファイルは特定の地域のみをカバーしているため、地図を適切な位置にパンする必要がある
2. **TileJSONのbounds**: 現在、デフォルト値（全世界）が設定されているため、実際のCOG範囲とは異なる場合がある
3. **CORS設定**: `allow_credentials=False`に設定（`allow_origins=["*"]`との併用制約のため）

---

## 7. 次のステップ（未実装）

### 高優先度

#### マップビューワーの初期表示位置改善

**目的**: タイルセットの実際のデータ範囲に自動的にフィットする

**現状の問題**:
- TileJSONのboundsがデフォルト値（全世界）になっている場合、地図がデータのない位置を表示する
- ユーザーが手動でパンしないとタイルが見えない

**実装方針**:
1. データソース登録時に実際のboundsを計算・保存
2. タイルセットのbounds/centerを自動更新するAPIエンドポイント追加
3. TilesetMapPreviewで「データ範囲にフィット」ボタンの動作を改善

**優先度**: 高

### 中優先度

#### フィーチャー地図表示の改善

**目的**: フィーチャー詳細ページでの地図表示を改善

**実装方針**:
1. 既存のMapViewコンポーネントを活用
2. フィーチャーのジオメトリをハイライト表示
3. 編集ページでの座標ピッカー改善

**優先度**: 中

#### 本番デプロイ

**対象**:
- API（CORS修正、PMTiles TileJSON修正）
- Admin UI（マップビューワー追加）

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

### 低優先度

#### タイルセット統計・分析機能

**目的**: タイルセットの利用状況やフィーチャー数などの統計表示

**実装方針**:
1. APIにフィーチャーカウントエンドポイント追加
2. ダッシュボードに統計グラフ追加
3. タイルセット詳細ページに統計カード追加

**優先度**: 低

### 完了した課題

#### ~~PMTiles用TileJSONエンドポイント修正~~ ✅ 完了

**症状**: pmtilesタイプのタイルセットでTileJSON取得時に500エラー

**原因**: `generate_pmtiles_tilejson()`関数の呼び出し時に引数が正しくマッピングされていなかった
- `name` → `tileset_name`に変更が必要
- 個別の引数を`metadata`辞書にまとめる必要があった

**修正内容**:
- `api/lib/main.py`の`get_tileset_tilejson`エンドポイント内で、pmtilesタイプの場合の`generate_pmtiles_tilejson()`呼び出しを修正

**ステータス**: ✅ 修正完了

#### ~~CORS設定の修正~~ ✅ 完了

**症状**: ブラウザからのタイルリクエストがCORSエラーでブロックされる

**原因**: `allow_origins=["*"]`と`allow_credentials=True`の組み合わせはブラウザで拒否される

**修正内容**:
- `api/lib/main.py`のCORSMiddleware設定を`allow_credentials=False`に変更

**ステータス**: ✅ 修正完了

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

### ~~4. PMTiles TileJSON 500エラー~~ ✅ 修正済み

**症状**: pmtilesタイプのタイルセット詳細ページでTileJSON取得時に500エラー

**修正済み**: `api/lib/main.py`の`generate_pmtiles_tilejson()`呼び出しの引数を修正

### 5. Next.js 16 Middleware警告

**症状**: ビルド時に `middleware` ファイル規約が非推奨との警告が表示される

**対応**: 次回メジャーアップデート時に `proxy` への移行を検討

---

## 8. 技術スタック

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
| PMTiles | aiopmtiles | 0.1.0 | ✅ Vercelで動作 |
| Raster Tiles | rio-tiler | 7.0+ | ⚠️ Vercelでは動作不可 |
| Authentication | Supabase Auth + PyJWT | - | ✅ JWT検証実装済み |
| Geocoding | Nominatim API | - | OpenStreetMap |
| Tile Format | MVT (pbf), PNG, WebP | - | |

---

## 9. ローカル開発環境セットアップ

### Docker PostgreSQL初期化

```fish
cd /path/to/geo-base/docker

# ボリューム削除して再初期化
docker compose down -v
docker compose up -d

# ログ確認（エラーがないこと）
docker compose logs -f postgis
```

### API起動

```fish
cd /path/to/geo-base/api
uv run uvicorn lib.main:app --reload --port 8000
```

### Admin UI起動

```fish
cd /path/to/geo-base/app
npm run dev
```

### 動作確認URL

| サービス | URL |
|---------|-----|
| API | http://localhost:8000 |
| Admin UI | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |

### テスト用サンプルデータ

ローカルテストで使用できるサンプルデータソース：

#### PMTiles
| 名前 | URL | 範囲 |
|------|-----|------|
| Protomaps Firenze | `https://protomaps.github.io/PMTiles/protomaps(vector)ODbL_firenze.pmtiles` | イタリア・フィレンツェ（緯度43.77, 経度11.25） |
| US ZCTAs | `https://r2-public.protomaps.com/protomaps-sample-datasets/cb_2018_us_zcta510_500k.pmtiles` | 米国全域 |

#### COG (Cloud Optimized GeoTIFF)
| 名前 | URL | 範囲 |
|------|-----|------|
| Sentinel-2 54TWN | `https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/54/T/WN/2023/11/S2B_54TWN_20231118_1_L2A/TCI.tif` | 北海道南部（緯度42.36〜43.34, 経度140.99〜142.35）, z7-13 |

**注意**: COGはローカル環境でのみ動作（Vercelでは rasterio が使用不可）

---

## 10. 本番環境URL一覧

| サービス | URL | プラットフォーム | 状態 |
|---------|-----|----------------|------|
| Admin UI | https://geo-base-app.vercel.app | Vercel | ✅ 稼働中 |
| API | https://geo-base-puce.vercel.app | Vercel | ✅ 稼働中 |
| MCP Server | https://geo-base-mcp.fly.dev | Fly.io | ✅ 稼働中 |

---

## 11. 参照資料

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
- [aiopmtiles](https://github.com/developmentseed/aiopmtiles)
- [rio-tiler](https://cogeotiff.github.io/rio-tiler/)

---

## 12. 変更履歴

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
| 2025-12-13 | 1.1.0 | フィーチャー管理UI（Step 3.4完了）、MapLibre GL JS統合、サンプルデータ投入スクリプト追加 |
| 2025-12-14 | 1.2.0 | 設定画面（Step 3.5完了）、ダッシュボードのタイルセット数表示修正 |
| 2025-12-14 | 1.3.0 | GeoJSONインポート機能（Step 3.7完了）、フィーチャー一覧にインポートボタン追加 |
| 2025-12-14 | 1.4.0 | データソース管理UI（Step 3.8完了）、PMTiles/COG接続テスト、aiopmtiles/rio-tiler互換性修正 |
| 2025-12-14 | 1.4.1 | PMTiles TileJSONエンドポイント500エラー修正（generate_pmtiles_tilejson引数修正） |
| 2025-12-14 | 1.5.0 | マップビューワー（Step 3.9完了）、TilesetMapPreviewコンポーネント追加、CORS設定修正 |

---

*このドキュメントは2025-12-14時点の情報です。APIバージョン: 0.4.0 / MCPバージョン: 0.2.0 / Admin UIバージョン: 0.8.0（Step 3.9完了）*
