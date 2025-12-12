# geo-base プロジェクト 引き継ぎドキュメント

**作成日**: 2025-12-12  
**最終更新**: 2025-12-12  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**本番URL**: https://geo-base-puce.vercel.app/  
**APIバージョン**: 0.3.0

---

## 1. プロジェクト概要

### 目的
地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーシステムの構築。MCPサーバーを通じてClaudeとの連携も可能にする。

### アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Admin UI      │     │   MCP Server    │     │   外部クライアント  │
│   (Next.js)     │     │   (FastMCP)     │     │   (MapLibre等)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Tile Server API     │
                    │   (FastAPI on Vercel)   │
                    │   ※将来: Fly.io移行予定  │
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

## 2. 完了した作業（フェーズ1）

### Step 1.1: プロジェクト初期設定 ✅
- Monorepo構造の作成
- 各サブプロジェクトの設定ファイル（pyproject.toml等）
- Docker Compose（ローカルPostGIS）
- データベーススキーマ設計

### Step 1.2: FastAPIタイルサーバー構築 ✅
- ヘルスチェックエンドポイント
- MBTilesからの静的タイル配信
- PostGISからの動的MVT生成
- TileJSON生成
- MapLibre GL JSプレビューページ

### Step 1.3: 動的タイル生成機能の充実 ✅
- 属性フィルタリング対応（`filter`パラメータ）
- ズームレベルに応じたジオメトリ簡略化
- キャッシュヘッダーの最適化

### Step 1.4: Vercelデプロイ ✅
- Supabase PostgreSQL + PostGIS接続
- Pooler接続（ポート6543）+ SSL
- 本番環境での動作確認

### Step 1.5: ラスタタイル対応（COG/GeoTIFF）⚠️ 部分完了
- rio-tilerによるCOGタイル生成モジュール実装
- ラスタタイルエンドポイント追加
- raster_sourcesテーブル追加
- **制限事項**: Vercel環境ではrio-tiler（GDAL依存）が動作しないため、ラスタタイル機能は利用不可
- **今後の方針**: Fly.ioへの移行時に有効化予定

### Step 1.6: PMTiles対応 ✅
- aiopmtilesライブラリによるHTTP Range Request対応
- PMTilesタイル配信エンドポイント追加
- pmtiles_sourcesテーブル追加
- TileJSON/メタデータエンドポイント
- **Vercelで動作確認済み**（ネイティブ依存なし）

### Step 1.7: 認証機能（Supabase Auth）✅
- JWT検証モジュール（lib/auth.py）
- 全タイルエンドポイントにアクセス制御追加
- `is_public=false` のタイルセットは認証必須
- `user_id` に基づくオーナー確認
- `/api/auth/me`, `/api/auth/status` エンドポイント
- RLSポリシー用SQL（04_rls_policies.sql）
- **ローカル・Vercel両環境で動作確認済み**

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
│   │   ├── pmtiles.py           # PMTilesユーティリティ【Step 1.6】
│   │   ├── raster_tiles.py      # ラスタータイル生成ユーティリティ
│   │   └── tiles.py             # ベクタータイル生成ユーティリティ
│   ├── data/                    # MBTilesファイル格納（ローカル用）
│   ├── index.py                 # Vercelエントリーポイント
│   ├── pyproject.toml
│   ├── uv.lock                  # 依存関係ロックファイル
│   ├── requirements.txt         # Vercel用依存関係
│   ├── runtime.txt              # Pythonバージョン指定
│   ├── .env.example
│   └── .python-version
├── mcp/                          # MCPサーバー（未実装）
│   ├── tools/
│   │   └── __init__.py
│   ├── pyproject.toml
│   ├── .env.example
│   └── .python-version
├── app/                          # Next.js管理画面（未実装）
│   └── src/
├── docker/
│   ├── docker-compose.yml       # ローカルPostGIS
│   └── postgis-init/
│       ├── 01_init.sql          # 基本スキーマ定義
│       ├── 02_raster_schema.sql # ラスターソーステーブル
│       ├── 03_pmtiles_schema.sql # PMTilesソーステーブル【Step 1.6】
│       └── 04_rls_policies.sql  # RLSポリシー【Step 1.7】
├── packages/                     # 共有パッケージ（未実装）
│   └── shared/
│       └── types/
├── scripts/
│   ├── setup.sh                 # 環境セットアップ
│   └── seed.sh                  # テストデータ投入
├── vercel.json                  # Vercel設定
├── DEPLOY.md                    # デプロイ手順書
├── HANDOVER.md                  # 引き継ぎドキュメント
├── README.md
└── .gitignore
```

---

## 4. 技術スタック

| レイヤー | 技術 | バージョン | 備考 |
|---------|------|-----------|------|
| API Framework | FastAPI | 0.115.x | |
| Database | PostgreSQL + PostGIS | 16 + 3.4 | |
| Database Hosting | Supabase | - | Auth, Storage含む |
| API Hosting | Vercel Serverless | Python 3.12 | 将来Fly.io移行予定 |
| Package Manager | uv | latest | |
| Vector Tiles | PostGIS ST_AsMVT | - | |
| PMTiles | aiopmtiles | 0.1.0 | ✅ Vercelで動作 |
| Raster Tiles | rio-tiler | 7.0+ | ⚠️ Vercelでは動作不可 |
| Authentication | Supabase Auth + PyJWT | - | ✅ JWT検証実装済み |
| Tile Format | MVT (pbf), PNG, WebP | - | |

### 主要ライブラリ

```
# api/pyproject.toml より
fastapi>=0.109.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
psycopg2-binary>=2.9.9
pymbtiles>=0.5.0
shapely>=2.0.0
geoalchemy2>=0.14.0
httpx>=0.26.0
aiopmtiles @ git+https://github.com/developmentseed/aiopmtiles.git  # PMTiles対応
PyJWT>=2.8.0                 # JWT検証
cryptography>=41.0.0         # JWT署名検証
rio-tiler>=7.0.0             # ⚠️ Vercelでは動作不可
rasterio>=1.4.0              # ⚠️ Vercelでは動作不可
```

---

## 5. 環境設定

### ローカル開発

```fish
# PostGIS起動
cd docker && docker compose up -d

# API起動
cd api
cp .env.example .env  # DATABASE_URL, SUPABASE_JWT_SECRETを設定
uv sync
uv run uvicorn lib.main:app --reload --port 3000
```

### 環境変数

| 変数名 | ローカル | 本番（Vercel） | 説明 |
|--------|---------|---------------|------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/geo_base` | `postgresql://postgres.xxx:[PASSWORD]@aws-0-xxx.pooler.supabase.com:6543/postgres` | DB接続文字列 |
| `ENVIRONMENT` | `development` | `production` | 環境識別 |
| `SUPABASE_JWT_SECRET` | (Supabaseから取得) | (Supabaseから取得) | JWT検証用シークレット |

**SUPABASE_JWT_SECRETの取得方法**:
Supabase Dashboard > Settings > API > JWT Secret

**重要**: Supabaseへの接続は**Pooler（ポート6543）**を使用すること。直接接続（ポート5432）はサーバーレス環境では接続枯渇の問題が発生する。

---

## 6. データベーススキーマ

### tilesets テーブル
```sql
CREATE TABLE tilesets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('raster', 'vector', 'pmtiles')),
    format VARCHAR(50) NOT NULL,
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 22,
    bounds GEOMETRY(POLYGON, 4326),
    center GEOMETRY(POINT, 4326),
    attribution TEXT,
    is_public BOOLEAN DEFAULT true,
    user_id UUID,                    -- Supabase Auth user ID
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### features テーブル
```sql
CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID REFERENCES tilesets(id) ON DELETE CASCADE,
    layer_name VARCHAR(255) DEFAULT 'default',
    geom GEOMETRY NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 空間インデックス
CREATE INDEX idx_features_geom ON features USING GIST (geom);
```

### raster_sources テーブル
```sql
CREATE TABLE raster_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL REFERENCES tilesets(id) ON DELETE CASCADE,
    cog_url TEXT NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'http',
    band_count INTEGER,
    band_descriptions JSONB DEFAULT '[]',
    statistics JSONB DEFAULT '{}',
    native_crs VARCHAR(50),
    native_resolution FLOAT,
    recommended_min_zoom INTEGER,
    recommended_max_zoom INTEGER,
    acquisition_date TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tileset_id)
);
```

### pmtiles_sources テーブル【Step 1.6】
```sql
CREATE TABLE pmtiles_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL REFERENCES tilesets(id) ON DELETE CASCADE,
    pmtiles_url TEXT NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'supabase',
    tile_type VARCHAR(20),           -- 'mvt', 'png', 'jpg', 'webp', 'avif'
    tile_compression VARCHAR(20),    -- 'gzip', 'brotli', 'zstd', 'none'
    min_zoom INTEGER,
    max_zoom INTEGER,
    bounds JSONB,
    center JSONB,
    layers JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tileset_id)
);
```

---

## 7. 実装済みAPIエンドポイント

### 認証エンドポイント【Step 1.7】

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/auth/me` | 必須 | 認証ユーザー情報取得 |
| GET | `/api/auth/status` | 不要 | 認証状態確認 |

### ヘルスチェック

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/health` | ヘルスチェック（rasterio, pmtiles, auth状態含む） |
| GET | `/api/health/db` | DB接続チェック |

### タイルセット管理

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/tilesets` | 不要※ | タイルセット一覧（公開のみ） |
| GET | `/api/tilesets?include_private=true` | 必要 | タイルセット一覧（自分の非公開含む） |
| GET | `/api/tilesets/{id}` | 条件付き | タイルセット詳細 |
| GET | `/api/tilesets/{id}/tilejson.json` | 条件付き | タイルセットのTileJSON |

※ `is_public=false` のタイルセットは認証必須

### ベクタータイル（Vercelで動作）

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/` | 不要 | プレビューページ（MapLibre GL JS） |
| GET | `/api/tiles/features/{z}/{x}/{y}.pbf` | 条件付き | フィーチャーMVTタイル |
| GET | `/api/tiles/features/tilejson.json` | 不要 | フィーチャーのTileJSON |
| GET | `/api/tiles/dynamic/{layer}/{z}/{x}/{y}.pbf` | 不要 | 動的MVTタイル |
| GET | `/api/tiles/mbtiles/{name}/{z}/{x}/{y}.{fmt}` | 不要 | MBTilesタイル（ローカル用） |

### PMTilesタイル【Step 1.6】（Vercelで動作）

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.{format}` | 条件付き | PMTilesタイル取得 |
| GET | `/api/tiles/pmtiles/{tileset_id}/tilejson.json` | 条件付き | TileJSON |
| GET | `/api/tiles/pmtiles/{tileset_id}/metadata` | 条件付き | PMTilesメタデータ |

### ラスタータイル（⚠️ Vercelでは動作不可）

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/tiles/raster/{tileset_id}/{z}/{x}/{y}.{format}` | 条件付き | ラスタタイル取得 |
| GET | `/api/tiles/raster/{tileset_id}/tilejson.json` | 条件付き | TileJSON |
| GET | `/api/tiles/raster/{tileset_id}/preview` | 条件付き | プレビュー画像 |
| GET | `/api/tiles/raster/{tileset_id}/info` | 条件付き | COGメタデータ |
| GET | `/api/tiles/raster/{tileset_id}/statistics` | 条件付き | バンド統計情報 |

### 認証・アクセス制御仕様【Step 1.7】

| タイルセット | 認証なし | 認証あり（オーナー） | 認証あり（他人） |
|-------------|---------|-------------------|----------------|
| `is_public=true` | ✅ 200 OK | ✅ 200 OK | ✅ 200 OK |
| `is_public=false` | ❌ 401 Unauthorized | ✅ 200 OK | ❌ 403 Forbidden |

---

## 8. 今後の課題と実装方針

### フェーズ1 残タスク

#### 8.1 ラスタタイル有効化（Fly.io移行時）

**現状**: コード実装済み、Vercelでは動作不可

**制限事項**:
- rio-tiler/rasterioはGDAL（ネイティブライブラリ）に依存
- Vercel Serverless環境ではネイティブ依存ライブラリが動作しない

**今後の方針**:
- API全体をFly.io（Docker）に移行時にラスタタイル機能を有効化
- MCPサーバーと同じインフラ基盤で統一

---

### フェーズ2: MCPサーバー機能（優先度: 高）

**目的**: Claude DesktopからGeoデータを検索・取得できるようにする

**技術スタック**:
- フレームワーク: FastMCP
- ホスティング: Fly.io
- プロトコル: MCP over HTTP/SSE

**実装予定ツール**:

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `list_tilesets` | タイルセット一覧取得 | `type?`, `is_public?` |
| `get_tileset` | タイルセット詳細取得 | `tileset_id` |
| `search_features` | フィーチャー検索 | `bbox?`, `layer?`, `filter?`, `limit?` |
| `get_tile` | タイルデータ取得 | `tileset_id`, `z`, `x`, `y` |
| `geocode` | 住所→座標変換 | `address` |
| `reverse_geocode` | 座標→住所変換 | `lat`, `lng` |

**ディレクトリ構造案**:
```
mcp/
├── server.py              # FastMCPサーバー
├── tools/
│   ├── __init__.py
│   ├── tilesets.py       # タイルセット関連ツール
│   ├── features.py       # フィーチャー関連ツール
│   └── geocoding.py      # ジオコーディングツール
├── pyproject.toml
└── Dockerfile            # Fly.io用
```

---

### フェーズ3: 管理画面（Next.js）（優先度: 中）

**目的**: タイルセットとフィーチャーの管理UI

**技術スタック**:
- フレームワーク: Next.js 14+ (App Router)
- UI: shadcn/ui + Tailwind CSS
- 地図: MapLibre GL JS
- 認証: Supabase Auth

**画面構成案**:

1. **ダッシュボード** (`/`)
   - タイルセット一覧
   - 使用統計

2. **タイルセット管理** (`/tilesets`)
   - 一覧表示
   - 作成・編集・削除
   - プレビュー地図

3. **フィーチャー管理** (`/tilesets/[id]/features`)
   - フィーチャー一覧
   - GeoJSON/Shapefileアップロード
   - 地図上での編集

4. **設定** (`/settings`)
   - APIキー管理
   - ユーザー設定

---

### 将来の移行計画: Vercel → Fly.io

**目的**: ラスタタイル機能の有効化、MCPサーバーとの統一基盤

**移行内容**:
- API（FastAPI）をDockerコンテナ化
- Fly.ioへデプロイ
- rio-tiler/rasterioの有効化
- MCPサーバーと同じインフラで運用

**Dockerfile案**:
```dockerfile
FROM python:3.12-slim

# GDAL依存関係インストール
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "lib.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 9. テスト方法

### 認証機能テスト（fish形式）

```fish
# 環境変数設定
set -x API_BASE "http://localhost:3000"  # またはVercel URL
set -x JWT_TOKEN "your-jwt-token"

# 認証状態確認（認証なし）
curl "$API_BASE/api/auth/status"

# 認証状態確認（認証あり）
curl -H "Authorization: Bearer $JWT_TOKEN" "$API_BASE/api/auth/status"

# 認証ユーザー情報取得（認証必須）
curl -H "Authorization: Bearer $JWT_TOKEN" "$API_BASE/api/auth/me"

# 公開タイルセット（認証不要）
curl "$API_BASE/api/tilesets/PUBLIC_TILESET_ID"

# 非公開タイルセット（認証必要）
curl -H "Authorization: Bearer $JWT_TOKEN" "$API_BASE/api/tilesets/PRIVATE_TILESET_ID"
```

### JWTトークン取得方法

```fish
set -x SUPABASE_URL "https://your-project.supabase.co"
set -x SUPABASE_ANON_KEY "your-anon-key"

curl -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "your-password"}'
```

---

## 10. 参照資料

### プロジェクト内ドキュメント
- `/mnt/project/geolocation-tech-source.txt` - タイルサーバー実装のサンプルコード
- `/mnt/project/PROJECT_ROADMAP.md` - プロジェクトロードマップ
- `/mnt/project/geo-base.txt` - 最新ソースコード

### 外部ドキュメント
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostGIS MVT Functions](https://postgis.net/docs/ST_AsMVT.html)
- [TileJSON Specification](https://github.com/mapbox/tilejson-spec)
- [Mapbox Vector Tile Specification](https://github.com/mapbox/vector-tile-spec)
- [PMTiles Specification](https://github.com/protomaps/PMTiles)
- [aiopmtiles](https://github.com/developmentseed/aiopmtiles)
- [Cloud Optimized GeoTIFF](https://www.cogeo.org/)
- [rio-tiler Documentation](https://cogeotiff.github.io/rio-tiler/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Fly.io Documentation](https://fly.io/docs/)

---

## 11. 注意事項・Tips

### Vercelデプロイ時の注意

1. **Python依存関係**: ネイティブ依存のあるライブラリ（rasterio等）は動作しない
2. **GitHubからのパッケージ**: `pyproject.toml`に`[tool.hatch.metadata] allow-direct-references = true`が必要
3. **接続タイムアウト**: Serverless Functionは最大30秒（Proプランで60秒）
4. **コールドスタート**: 初回リクエストは遅延する可能性がある
5. **モジュールパス**: `index.py`で`sys.path`の調整が必要
6. **Deployment Protection**: プレビューブランチではVercel認証が有効になる場合がある

### Supabase接続の注意

1. **Pooler必須**: サーバーレス環境では必ずPooler接続（ポート6543）を使用
2. **SSL必須**: `?sslmode=require` が自動付与される
3. **PostGIS拡張**: 手動で `CREATE EXTENSION postgis;` が必要
4. **JWT Secret**: Settings > API から取得

### ローカル開発Tips（fish形式）

```fish
# APIディレクトリで実行
cd api
uv run uvicorn lib.main:app --reload --port 3000

# PostgreSQLに接続
docker compose -f docker/docker-compose.yml exec -T postgis psql -U postgres -d geo_base

# テストデータ投入
docker compose -f docker/docker-compose.yml exec -T postgis psql -U postgres -d geo_base -c "
INSERT INTO tilesets (id, name, type, format, is_public, user_id)
VALUES 
    ('a0000000-0000-0000-0000-000000000001', 'Public Test', 'vector', 'pbf', true, NULL),
    ('a0000000-0000-0000-0000-000000000002', 'Private Test', 'vector', 'pbf', false, 'YOUR_USER_ID')
ON CONFLICT (id) DO NOTHING;
"
```

---

## 12. 連絡先・引き継ぎ情報

- **GitHub**: https://github.com/mopinfish/geo-base
- **本番環境**: https://geo-base-puce.vercel.app/
- **Supabaseプロジェクト**: `zxpfupcxwfzfjvpfadww`

---

## 13. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-12 | 0.1.0 | 初版作成（Step 1.1〜1.4完了） |
| 2025-12-12 | 0.2.0 | ラスタタイル対応（Step 1.5）、PMTiles対応（Step 1.6）追加 |
| 2025-12-12 | 0.3.0 | 認証機能（Step 1.7）追加、アクセス制御実装 |

---

*このドキュメントは2025-12-12時点の情報です。APIバージョン: 0.3.0*
