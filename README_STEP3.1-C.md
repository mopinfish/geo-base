# geo-base Step 3.1-C: COG Support 実装

## 概要

このパッケージには、Cloud Optimized GeoTIFF (COG) サポートの実装が含まれています。

### 新機能

1. **COGファイルアップロード** - Supabase Storageへのアップロード
2. **カラーマッププリセット** - NDVI、地形、温度など多数のプリセット
3. **ラスターマッププレビュー強化** - opacity調整、カラーマップ選択UI

## ファイル構成

```
api/lib/
├── storage.py              # 新規: Supabase Storageアップロードモジュール
├── raster_tiles.py         # 更新: カラーマッププリセット追加
└── main_additions.py       # 参考: main.pyに追加するコード

app/src/components/map/
└── tileset-map-preview.tsx # 更新: ラスター対応強化
```

## 適用手順

### 1. ファイルの配置

```bash
cd /path/to/geo-base

# zipを解凍して上書き
unzip -o ~/Downloads/geo-base-step3.1-c.zip -d .
```

### 2. main.pyの手動修正

`api/lib/main_additions.py` の内容を `api/lib/main.py` に統合する必要があります。

#### 2.1 import追加（main.pyの先頭部分）

```python
# 既存のimportの後に追加
from fastapi import UploadFile, File

# lib.raster_tilesのimportに追加
from lib.raster_tiles import (
    RASTER_MEDIA_TYPES,
    is_rasterio_available,
    get_raster_tile_async,
    get_raster_preview,
    get_raster_preview_async,  # 追加
    get_cog_info,
    get_cog_statistics,
    generate_raster_tilejson,
    get_raster_cache_headers,
    get_raster_media_type,
    validate_tile_format,
    list_colormaps,           # 追加
    validate_cog,             # 追加
)

# 新規import追加
from lib.storage import (
    SupabaseStorageClient,
    get_storage_client,
    validate_cog_file,
    extract_cog_metadata,
    MAX_FILE_SIZE,
    COG_EXTENSIONS,
)
```

#### 2.2 カラーマップAPIエンドポイント追加

`@app.get("/api/datasources")` の前に以下を追加：

```python
# ============================================================================
# Colormap API Endpoints
# ============================================================================

@app.get("/api/colormaps")
def get_colormaps():
    """List all available colormaps for raster visualization."""
    # ... (main_additions.pyを参照)

@app.get("/api/colormaps/{name}")
def get_colormap_info(name: str):
    """Get information about a specific colormap."""
    # ... (main_additions.pyを参照)
```

#### 2.3 COGUploadResponseモデル追加

Pydanticモデル定義セクションに追加：

```python
class COGUploadResponse(BaseModel):
    """Response model for COG upload."""
    id: str
    tileset_id: str
    type: str = "cog"
    url: str
    storage_provider: str
    band_count: Optional[int] = None
    band_descriptions: Optional[List[str]] = None
    native_crs: Optional[str] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    bounds: Optional[List[float]] = None
    center: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
```

#### 2.4 COGアップロードエンドポイント追加

`@app.delete("/api/datasources/{datasource_id}")` の前に以下を追加：

```python
@app.post("/api/datasources/cog/upload", response_model=COGUploadResponse)
async def upload_cog_file(...):
    """Upload a Cloud Optimized GeoTIFF (COG) file."""
    # ... (main_additions.pyを参照)
```

#### 2.5 ラスタープレビューエンドポイント更新

既存の `@app.get("/api/tiles/raster/{tileset_id}/preview")` を `main_additions.py` の実装で置き換え。

### 3. Supabase Storage設定

#### 3.1 環境変数

```bash
# .env または Fly.io secrets
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

#### 3.2 Supabaseダッシュボードでバケット作成

1. Supabaseダッシュボード → Storage
2. 「New bucket」をクリック
3. バケット名: `geo-tiles`
4. Public bucketに設定（または必要に応じてprivate）

### 4. デプロイ

```bash
# ローカルテスト
cd api
uv run uvicorn lib.main:app --reload

# Fly.ioデプロイ
fly deploy -c fly.api.toml

# Vercel Admin UIデプロイ
cd app
vercel --prod
```

### 5. 動作確認

```bash
# ヘルスチェック
curl https://geo-base-api.fly.dev/api/health

# カラーマップ一覧
curl https://geo-base-api.fly.dev/api/colormaps

# COGアップロード（認証必要）
curl -X POST "https://geo-base-api.fly.dev/api/datasources/cog/upload?tileset_id=YOUR_TILESET_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@your-file.tif"
```

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

## API仕様

### GET /api/colormaps
カラーマップ一覧を取得

### GET /api/colormaps/{name}
特定のカラーマップの詳細（カラーストップ）を取得

### POST /api/datasources/cog/upload
COGファイルをアップロード

- Query: `tileset_id` (必須)
- Body: `file` (multipart/form-data)
- 認証必須

### GET /api/tiles/raster/{tileset_id}/preview
ラスタープレビュー画像を取得

- Query: `max_size`, `bands`, `scale_min`, `scale_max`, `colormap`, `format`

## 注意事項

1. **ファイルサイズ制限**: 最大500MB
2. **対応形式**: .tif, .tiff, .geotiff
3. **COG推奨**: Cloud Optimized GeoTIFFを推奨（内部タイリング、オーバービュー付き）
4. **認証**: アップロードには認証が必要
