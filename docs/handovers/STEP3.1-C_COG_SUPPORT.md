# geo-base Step 3.1-C: COGサポート強化

## 概要

Cloud Optimized GeoTIFF (COG) のサポートを強化し、以下の機能を追加しました：

- **RGB画像の自動スケーリング** - 3バンド以上の画像は自動的に0-255スケールを適用
- **カラーマッププリセット** - NDVI、地形、温度など多数のプリセット
- **マッププレビューUI改善** - opacity調整、カラーマップ選択
- **Supabase Storageアップロード** - COGファイルのアップロード機能

## 含まれるファイル

```
api/lib/
├── main.py                 # 更新: band_count取得・自動スケーリング対応
├── storage.py              # 新規: Supabase Storageアップロードモジュール
├── raster_tiles.py         # 更新: カラーマッププリセット追加
└── main_additions.py       # 参考: 追加エンドポイントのサンプルコード

app/src/components/map/
└── tileset-map-preview.tsx # 更新: ラスター対応強化（opacity, colormap）
```

## 主な変更点

### 1. RGB画像の自動スケーリング (main.py, raster_tiles.py)

**問題**: Sentinel-2等のRGB画像（0-255）がデフォルトスケール（0-3000）で暗く表示されていた

**解決**: 
- ラスターTileJSONエンドポイントでCOGのband_countを取得
- `generate_raster_tilejson`関数に`band_count`引数を追加
- 3バンド以上の画像は自動的に`scale_min=0&scale_max=255`をタイルURLに追加

### 2. マッププレビューUI (tileset-map-preview.tsx)

- 「表示設定」パネルを追加
- 不透明度スライダー（0-100%）
- カラーマップ選択ドロップダウン
- Style not loadedエラーの修正

## 適用手順

### 1. ファイルの配置

```bash
cd /path/to/geo-base

# zipを解凍して上書き（main.pyも含まれます）
unzip -o ~/Downloads/geo-base-step3.1-c.zip -d .
```

### 2. 依存パッケージの追加

```bash
cd api
uv add python-multipart
```

### 3. コミット & プッシュ

```bash
git add .
git commit -m "feat(api): Step 3.1-C - COGサポート強化

- RGB画像の自動スケーリング（0-255）
- カラーマッププリセット対応
- マッププレビューUI改善（opacity, colormap選択）
- Supabase Storage統合モジュール追加"
git push origin develop
```

## テスト方法

### 1. APIサーバー起動

```bash
cd api && uv run uvicorn lib.main:app --reload --port 8000
```

### 2. TileJSON確認

```bash
# RGB画像の場合、scale_min/scale_maxがURLに含まれることを確認
curl "http://localhost:8000/api/tiles/raster/{tileset_id}/tilejson.json"
```

期待される出力（RGB画像の場合）:
```json
{
  "tiles": ["http://localhost:8000/api/tiles/raster/.../png?scale_min=0&scale_max=255"]
}
```

### 3. プレビュー確認

```bash
# デフォルト
curl -o preview.png "http://localhost:8000/api/tiles/raster/{tileset_id}/preview"

# スケール指定
curl -o preview_scaled.png "http://localhost:8000/api/tiles/raster/{tileset_id}/preview?scale_min=0&scale_max=255"
```

### 4. Admin UI確認

1. http://localhost:3000 にアクセス
2. ラスタータイルセットを選択
3. マッププレビューで「表示設定」パネルを確認
4. 不透明度・カラーマップ切り替えが動作することを確認

## カラーマッププリセット

| 名前 | 説明 | 用途 |
|------|------|------|
| `ndvi` | 植生指数 | 赤→黄→緑（-1〜1） |
| `terrain` | 地形 | 緑→茶→白（標高） |
| `temperature` | 温度 | 青→白→赤（低温→高温） |
| `precipitation` | 降水量 | 白→青→紫 |
| `bathymetry` | 水深 | 深青→水色→緑 |
| `grayscale` | グレースケール | 黒→白 |
| `viridis` | Viridis | 紫→緑→黄（知覚的に均一） |

## 追加エンドポイント（オプション）

`main_additions.py`には以下の追加エンドポイントのサンプルコードがあります。必要に応じてmain.pyに統合してください：

- `GET /api/colormaps` - カラーマップ一覧
- `GET /api/colormaps/{name}` - カラーマップ詳細
- `POST /api/datasources/cog/upload` - COGファイルアップロード

## 注意事項

1. **RGB画像の自動検出**: band_count >= 3 の場合、自動的に0-255スケールを適用
2. **単バンド画像**: DEMなどの単バンド画像はデフォルトスケール（手動指定可）
3. **カラーマップ**: 単バンド画像にのみ適用（RGB画像には無効）
