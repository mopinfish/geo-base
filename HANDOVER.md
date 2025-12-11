# geo-base プロジェクト 引き継ぎドキュメント

**作成日**: 2025-12-12  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**本番URL**: https://geo-base-puce.vercel.app/

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
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   PostgreSQL + PostGIS  │
                    │      (Supabase)         │
                    └─────────────────────────┘
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

---

## 3. 現在のファイル構成

```
geo-base/
├── api/                          # FastAPI タイルサーバー
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── config.py            # 設定管理（pydantic-settings）
│   │   ├── database.py          # DB接続（サーバーレス対応）
│   │   ├── main.py              # FastAPIアプリ・エンドポイント
│   │   └── tiles.py             # タイル生成ユーティリティ
│   ├── data/                    # MBTilesファイル格納（ローカル用）
│   ├── index.py                 # Vercelエントリーポイント
│   ├── pyproject.toml
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
│       └── 01_init.sql          # スキーマ定義
├── packages/                     # 共有パッケージ（未実装）
│   └── shared/
│       └── types/
├── scripts/
│   ├── setup.sh                 # 環境セットアップ
│   └── seed.sh                  # テストデータ投入
├── vercel.json                  # Vercel設定
├── DEPLOY.md                    # デプロイ手順書
├── README.md
└── .gitignore
```

---

## 4. 技術スタック

| レイヤー | 技術 | バージョン |
|---------|------|-----------|
| API Framework | FastAPI | 0.115.x |
| Database | PostgreSQL + PostGIS | 16 + 3.4 |
| Database Hosting | Supabase | - |
| API Hosting | Vercel Serverless | Python 3.12 |
| Package Manager | uv | latest |
| Vector Tiles | PostGIS ST_AsMVT | - |
| Tile Format | MVT (pbf) | - |

### 主要ライブラリ

```
# api/requirements.txt より
fastapi==0.115.6
pydantic==2.10.3
pydantic-settings==2.6.1
psycopg2-binary==2.9.10
pymbtiles==0.5.0
shapely==2.0.6
geoalchemy2==0.15.2
httpx==0.28.1
```

---

## 5. 環境設定

### ローカル開発

```bash
# PostGIS起動
cd docker && docker compose up -d

# API起動
cd api
cp .env.example .env  # DATABASE_URLをローカル用に設定
uv sync
uv run uvicorn lib.main:app --reload --port 3000
```

### 本番環境（Vercel）

環境変数:
| 変数名 | 値 |
|--------|-----|
| `DATABASE_URL` | `postgresql://postgres.xxx:[PASSWORD]@aws-0-xxx.pooler.supabase.com:6543/postgres` |
| `ENVIRONMENT` | `production` |

**重要**: Supabaseへの接続は**Pooler（ポート6543）**を使用すること。直接接続（ポート5432）はサーバーレス環境では接続枯渇の問題が発生する。

---

## 6. データベーススキーマ

### tilesets テーブル
```sql
CREATE TABLE tilesets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('raster', 'vector')),
    format VARCHAR(50) NOT NULL,
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 22,
    bounds GEOMETRY(POLYGON, 4326),
    center GEOMETRY(POINT, 4326),
    attribution TEXT,
    is_public BOOLEAN DEFAULT false,
    user_id UUID,
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

---

## 7. 実装済みAPIエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | プレビューページ（MapLibre GL JS） |
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/health/db` | DB接続チェック |
| GET | `/api/tilesets` | タイルセット一覧 |
| GET | `/api/tilesets/{id}` | タイルセット詳細 |
| GET | `/api/tilesets/{id}/tilejson.json` | タイルセットのTileJSON |
| GET | `/api/tiles/features/{z}/{x}/{y}.pbf` | フィーチャーMVTタイル |
| GET | `/api/tiles/features/tilejson.json` | フィーチャーのTileJSON |
| GET | `/api/tiles/dynamic/{layer}/{z}/{x}/{y}.pbf` | 動的MVTタイル |
| GET | `/api/tiles/mbtiles/{name}/{z}/{x}/{y}.{fmt}` | MBTilesタイル（ローカル用） |

### フィルタリング機能

`/api/tiles/features/{z}/{x}/{y}.pbf` は以下のクエリパラメータをサポート:

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `tileset_id` | タイルセットIDでフィルタ | `tileset_id=uuid` |
| `layer` | レイヤー名でフィルタ | `layer=landmarks` |
| `filter` | 属性フィルタ式 | `filter=properties.type=station` |
| `simplify` | 簡略化の有効/無効 | `simplify=false` |

#### フィルタ式の構文

```
# 単純等価
properties.type=station

# 複数値（OR）
properties.type=station,landmark

# パターンマッチ
properties.name~Tokyo

# 複数条件（AND）
properties.type=station;properties.name~Tokyo

# 否定
properties.type!=temple

# 数値比較
properties.population>1000000
```

---

## 8. 今後の課題と実装方針

### フェーズ1 追加機能（優先度: 高）

#### 8.1 ラスタタイル対応（COG/GeoTIFF）

**目的**: Cloud Optimized GeoTIFF (COG) からラスタタイルを動的に切り出す

**実装方針**:
1. `rio-tiler` ライブラリを使用
2. COGファイルはVercel BlobまたはSupabase Storageに格納
3. 新規エンドポイント: `/api/tiles/raster/{tileset_id}/{z}/{x}/{y}.{format}`

**参考コード** (`geolocation-tech-source.txt` より):
```python
from rio_tiler.io import COGReader

def get_raster_tile(cog_url: str, z: int, x: int, y: int):
    with COGReader(cog_url) as cog:
        img = cog.tile(x, y, z)
        return img.render(img_format="PNG")
```

**注意点**:
- `rasterio`, `rio-tiler` はネイティブ依存があるため、Vercelでの動作確認が必要
- 動作しない場合はAWS Lambda + Docker Imageでの代替を検討

#### 8.2 PMTiles対応

**目的**: PMTiles形式のタイルアーカイブに対応

**実装方針**:
1. `pmtiles` Pythonライブラリを使用
2. PMTilesファイルはHTTPレンジリクエストでアクセス
3. 新規エンドポイント: `/api/tiles/pmtiles/{tileset_name}/{z}/{x}/{y}.{format}`

**参考コード**:
```python
from pmtiles.reader import Reader, MmapSource, HttpSource

def get_pmtiles_tile(pmtiles_url: str, z: int, x: int, y: int):
    with Reader(HttpSource(pmtiles_url)) as reader:
        tile_data = reader.get(z, x, y)
        return tile_data
```

#### 8.3 認証機能（Supabase Auth）

**目的**: タイルセットへのアクセス制御

**実装方針**:
1. Supabase Auth JWTトークン検証
2. `is_public=false` のタイルセットは認証必須
3. Row Level Security (RLS) の活用

**実装ステップ**:
1. Supabase Auth設定
2. JWT検証ミドルウェア追加
3. `user_id` に基づくアクセス制御
4. RLSポリシー設定

---

### フェーズ2: MCPサーバー機能（優先度: 中）

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

**Fly.io デプロイ**:
```bash
fly launch --name geo-base-mcp
fly secrets set DATABASE_URL=...
fly deploy
```

---

### フェーズ3: 管理画面（Next.js）（優先度: 低）

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

## 9. 参照資料

### プロジェクト内ドキュメント
- `/mnt/project/geolocation-tech-source.txt` - タイルサーバー実装のサンプルコード
- `/mnt/project/PROJECT_ROADMAP.md` - プロジェクトロードマップ
- `/mnt/project/geo-base.txt` - 要件定義

### 外部ドキュメント
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostGIS MVT Functions](https://postgis.net/docs/ST_AsMVT.html)
- [TileJSON Specification](https://github.com/mapbox/tilejson-spec)
- [Mapbox Vector Tile Specification](https://github.com/mapbox/vector-tile-spec)
- [PMTiles Specification](https://github.com/protomaps/PMTiles)
- [Cloud Optimized GeoTIFF](https://www.cogeo.org/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Supabase Documentation](https://supabase.com/docs)

---

## 10. 注意事項・Tips

### Vercelデプロイ時の注意

1. **Python依存関係**: ネイティブ依存のあるライブラリ（rasterio等）は動作しない可能性がある
2. **接続タイムアウト**: Serverless Functionは最大30秒（Proプランで60秒）
3. **コールドスタート**: 初回リクエストは遅延する可能性がある

### Supabase接続の注意

1. **Pooler必須**: サーバーレス環境では必ずPooler接続（ポート6543）を使用
2. **SSL必須**: `?sslmode=require` が自動付与される
3. **PostGIS拡張**: 手動で `CREATE EXTENSION postgis;` が必要

### ローカル開発Tips

```bash
# APIディレクトリで実行すること
cd api
uv run uvicorn lib.main:app --reload --port 3000

# テストデータ投入
cd .. && bash scripts/seed.sh
```

---

## 11. 連絡先・引き継ぎ情報

- **GitHub**: https://github.com/mopinfish/geo-base
- **本番環境**: https://geo-base-puce.vercel.app/
- **Supabaseプロジェクト**: `zxpfupcxwfzfjvpfadww`

---

*このドキュメントは2025-12-12時点の情報です。*
