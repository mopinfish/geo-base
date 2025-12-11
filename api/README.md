# geo-base API

FastAPI-based Tile Server for geo-base.

## 機能

- 静的タイル配信（PNG, JPG, MVT/pbf）
- 動的タイル生成（PostGIS ST_AsMVT）
- MBTiles / PMTiles サポート
- タイルセット管理API

## セットアップ

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動
uv run uvicorn lib.main:app --reload --port 3000
```

## 環境変数

`.env.example`を参照してください。
