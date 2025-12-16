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
```

## API エンドポイント

- `GET /api/health` - ヘルスチェック
- `GET /api/tilesets` - タイルセット一覧
- `GET /api/tilesets/{id}` - タイルセット詳細
- `GET /api/tiles/{id}/{z}/{x}/{y}.pbf` - ベクタータイル取得
- `GET /api/tiles/{id}/{z}/{x}/{y}.png` - ラスタータイル取得

## ライセンス

MIT
