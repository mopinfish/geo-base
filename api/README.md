# geo-base API

FastAPI タイルサーバー - ベクター/ラスター地理データ配信API

## 概要

geo-base APIは、PostGISデータベースからベクタータイル（MVT）を動的に生成し、PMTilesやCloud Optimized GeoTIFF（COG）形式のラスターデータも配信できる地理空間タイルサーバーです。

## 機能

- **ベクタータイル**: PostGIS ST_AsMVTによる動的MVT生成
- **PMTiles**: クラウドネイティブなベクタータイル形式のサポート
- **ラスタータイル**: rio-tilerによるCOGタイル生成（Fly.io環境）
- **認証**: Supabase Auth JWT トークン検証
- **CRUD API**: タイルセット・フィーチャー管理

## プロジェクト構造

```
api/
├── lib/
│   ├── main.py              # アプリケーションエントリポイント
│   ├── models/              # Pydanticモデル
│   │   ├── tileset.py       # TilesetCreate, TilesetUpdate
│   │   ├── feature.py       # FeatureCreate, FeatureUpdate, Bulk系
│   │   └── datasource.py    # DatasourceCreate, DatasourceUpdate
│   ├── routers/             # FastAPI APIRouter
│   │   ├── health.py        # /api/health, /api/auth
│   │   ├── tilesets.py      # /api/tilesets CRUD
│   │   ├── features.py      # /api/features CRUD
│   │   ├── datasources.py   # /api/datasources CRUD
│   │   ├── colormaps.py     # /api/colormaps
│   │   ├── stats.py         # /api/stats
│   │   └── tiles/           # タイル配信
│   │       ├── mbtiles.py   # MBTiles
│   │       ├── dynamic.py   # Dynamic vector tiles
│   │       ├── pmtiles.py   # PMTiles
│   │       └── raster.py    # COG raster tiles
│   ├── config.py            # 設定
│   ├── database.py          # DB接続
│   ├── auth.py              # 認証
│   ├── cache.py             # キャッシュ
│   ├── tiles.py             # タイル生成ユーティリティ
│   ├── pmtiles.py           # PMTiles処理
│   ├── raster_tiles.py      # ラスタータイル処理
│   └── storage.py           # ストレージ (S3/Supabase)
├── Dockerfile               # Fly.io用Dockerイメージ
├── pyproject.toml           # Python依存関係 (uv)
└── uv.lock                  # ロックファイル
```

## デプロイ

### Fly.io（推奨）

```bash
cd api
fly deploy
```

詳細は [FLY_DEPLOY.md](./FLY_DEPLOY.md) を参照してください。

### Vercel

```bash
vercel deploy
```

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL接続文字列 | ✅ |
| `SUPABASE_URL` | Supabaseエンドポイント | ✅ |
| `SUPABASE_JWT_SECRET` | JWT検証シークレット | ✅ |
| `ENVIRONMENT` | 環境名（production/development） | ❌ |

## 開発

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動
uv run uvicorn lib.main:app --reload --port 8000

# APIドキュメント
open http://localhost:8000/docs
```

## API エンドポイント

### Health & Auth
- `GET /api/health` - ヘルスチェック
- `GET /api/health/db` - DB接続チェック
- `GET /api/auth/me` - 現在のユーザー情報
- `GET /api/auth/status` - 認証ステータス

### Tilesets
- `GET /api/tilesets` - タイルセット一覧
- `GET /api/tilesets/{id}` - タイルセット詳細
- `GET /api/tilesets/{id}/tilejson.json` - TileJSON
- `POST /api/tilesets` - タイルセット作成
- `PATCH /api/tilesets/{id}` - タイルセット更新
- `DELETE /api/tilesets/{id}` - タイルセット削除

### Features
- `GET /api/features` - フィーチャー一覧
- `POST /api/features` - フィーチャー作成
- `POST /api/features/bulk` - 一括インポート

### Tiles
- `GET /api/tiles/features/{z}/{x}/{y}.pbf` - ベクタータイル取得
- `GET /api/tiles/pmtiles/{id}/{z}/{x}/{y}.pbf` - PMTilesタイル
- `GET /api/tiles/raster/{id}/{z}/{x}/{y}.png` - ラスタータイル取得

### Datasources
- `GET /api/datasources` - データソース一覧
- `POST /api/datasources` - データソース作成
- `POST /api/datasources/cog/upload` - COGアップロード

### Stats & Colormaps
- `GET /api/stats` - 統計情報
- `GET /api/colormaps` - カラーマップ一覧

## ライセンス

MIT
