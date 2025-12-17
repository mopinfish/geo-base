# geo-base Season 3 引き継ぎドキュメント

**作成日**: 2025-12-17  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**現在のブランチ**: `develop`

---

## 1. 現在のシステム状況

### 1.1 デプロイ状況

| コンポーネント | ステータス | URL | バージョン |
|---------------|-----------|-----|-----------|
| API Server (Fly.io) | ✅ 稼働中 | https://geo-base-api.fly.dev | 0.4.0 |
| MCP Server (Fly.io) | ✅ 稼働中 | https://geo-base-mcp.fly.dev | 0.2.5 |
| Admin UI (Vercel) | ✅ 稼働中 | https://geo-base-admin.vercel.app | 0.4.0 |

> **Note**: Vercel版API（geo-base-puce.vercel.app）は廃止済み。すべてのコンポーネントがFly.io APIを参照。

### 1.2 Season 3 進捗サマリー

| ステップ | 内容 | ステータス |
|---------|------|-----------|
| Step 3.1-A | Fly.io移行準備（Dockerfile, fly.toml） | ✅ 完了 |
| Step 3.1-B | API移行・動作確認 | ✅ 完了 |
| Step 3.1-C | COGサポート | ✅ 完了 |
| Step 3.1-D | ラスター分析 | ✅ 完了 |
| Step 3.1-E | Admin UI更新 | ✅ 完了 |
| **main.pyリファクタリング** | 4,124行 → 150行にモジュール分割 | ✅ **完了** |
| Step 3.2 | データ品質・キャッシュ | 🔜 次のステップ |

---

## 2. 完了した作業

### 2.1 Phase 1: Fly.io移行 & ラスター機能 ✅

#### Step 3.1-A ~ 3.1-E（前回セッション完了）

- Dockerfile作成（GDAL 3.8 + Python 3.11 + uv環境）
- fly.toml設定（東京リージョン、auto-scaling）
- API移行・動作確認完了
- COGサポート実装
- ラスター分析機能（カラーマップ、プレビュー、統計）
- Admin UI ラスター対応

### 2.2 main.py リファクタリング ✅ **（今回完了）**

`api/lib/main.py`を**4,124行から約150行**に軽量化し、モジュール構造に分割しました。

#### 新しいファイル構造

```
api/lib/
├── main.py                 # エントリポイント (~150行)
├── models/
│   ├── __init__.py         # モデルexport
│   ├── tileset.py          # TilesetCreate, TilesetUpdate
│   ├── feature.py          # FeatureCreate, FeatureUpdate, BulkFeature系
│   └── datasource.py       # DatasourceCreate, DatasourceUpdate, Enums
├── routers/
│   ├── __init__.py         # ルーター説明
│   ├── health.py           # Health/Auth endpoints (~100行)
│   ├── tilesets.py         # Tilesets CRUD (~650行)
│   ├── features.py         # Features CRUD (~500行)
│   ├── datasources.py      # Datasources CRUD (~750行)
│   ├── colormaps.py        # Colormap endpoints (~80行)
│   ├── stats.py            # Statistics endpoints (~120行)
│   └── tiles/
│       ├── __init__.py     # Tiles router統合
│       ├── mbtiles.py      # MBTiles endpoints (~70行)
│       ├── dynamic.py      # Dynamic vector tiles (~160行)
│       ├── pmtiles.py      # PMTiles endpoints (~250行)
│       └── raster.py       # Raster tiles endpoints (~400行)
```

#### 修正したバグ

1. **ラスタータイルのスケーリング問題**
   - 問題: RGB画像が暗く表示される
   - 原因: router側で`scale_min`/`scale_max`にデフォルト値（0-3000）を強制設定
   - 解決: Noneのまま渡し、`raster_tiles.py`内で自動検出させる

2. **HTTPS Mixed Content問題**
   - 問題: TileJSONがhttp://で返され、HTTPSページからブロックされる
   - 原因: `get_base_url`関数がFly.io環境で正しくプロトコルを検出できない
   - 解決: 非localhost環境では強制的にHTTPSを使用

---

## 3. 現在のAPI エンドポイント一覧

### Health & Auth
```
GET  /api/health
GET  /api/health/db
GET  /api/health/cache
POST /api/admin/cache/clear
GET  /api/auth/me
GET  /api/auth/status
```

### Tilesets CRUD
```
GET    /api/tilesets
GET    /api/tilesets/{tileset_id}
GET    /api/tilesets/{tileset_id}/tilejson.json
GET    /api/tilesets/{tileset_id}/stats
POST   /api/tilesets
POST   /api/tilesets/{tileset_id}/calculate-bounds
PATCH  /api/tilesets/{tileset_id}
DELETE /api/tilesets/{tileset_id}
```

### Features CRUD
```
POST   /api/features
POST   /api/features/bulk
GET    /api/features
GET    /api/features/{feature_id}
PATCH  /api/features/{feature_id}
DELETE /api/features/{feature_id}
```

### Tiles
```
GET  /api/tiles/mbtiles/{tileset_name}/{z}/{x}/{y}.{format}
GET  /api/tiles/mbtiles/{tileset_name}/metadata.json
GET  /api/tiles/dynamic/{layer_name}/{z}/{x}/{y}.pbf
GET  /api/tiles/dynamic/{layer_name}/tilejson.json
GET  /api/tiles/features/{z}/{x}/{y}.pbf
GET  /api/tiles/features/tilejson.json
GET  /api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.{format}
GET  /api/tiles/pmtiles/{tileset_id}/tilejson.json
GET  /api/tiles/pmtiles/{tileset_id}/metadata
GET  /api/tiles/raster/{tileset_id}/{z}/{x}/{y}.{format}
GET  /api/tiles/raster/{tileset_id}/tilejson.json
GET  /api/tiles/raster/{tileset_id}/preview
GET  /api/tiles/raster/{tileset_id}/info
GET  /api/tiles/raster/{tileset_id}/statistics
```

### Datasources
```
GET    /api/datasources
GET    /api/datasources/{datasource_id}
POST   /api/datasources
POST   /api/datasources/cog/upload
POST   /api/datasources/{datasource_id}/test
DELETE /api/datasources/{datasource_id}
```

### Other
```
GET  /api/colormaps
GET  /api/colormaps/{name}
GET  /api/stats
```

---

## 4. 次のステップ: Phase 2（データ品質 & パフォーマンス最適化）

### 4.1 Step 3.2-A: バリデーション強化

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| bounds計算修正 | GeoJSONインポート時の正確な計算 | 1日 |
| center計算改善 | 重心計算の精度向上 | 0.5日 |
| 既存データ修正 | マイグレーションスクリプト | 0.5日 |
| バリデーション強化 | インポート前の検証 | 1日 |

### 4.2 Step 3.2-B: リトライ機能の完全統合

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| tilesets.py統合 | retry.pyの関数を適用 | 0.5日 |
| features.py統合 | retry.pyの関数を適用 | 0.5日 |
| API層リトライ | FastAPIレベルでのリトライ | 1日 |
| テスト追加 | リトライシナリオのテスト | 0.5日 |

### 4.3 Step 3.2-C: Redisキャッシュ導入

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| Redis/Upstash設定 | Fly.ioでのRedis設定 | 0.5日 |
| タイルキャッシュ | MVT/ラスタータイルのキャッシュ | 1.5日 |
| TileJSONキャッシュ | メタデータのキャッシュ | 0.5日 |
| キャッシュ無効化 | データ更新時の自動クリア | 1日 |

### 4.4 Step 3.2-D: バッチ処理最適化

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| 一括作成API最適化 | POST `/api/features/bulk` のパフォーマンス改善 | 1日 |
| 一括更新API | PATCH `/api/features/bulk` | 1日 |
| 一括削除API | DELETE `/api/features/bulk` | 0.5日 |
| MCPツール追加 | バッチ操作用ツール | 1日 |

---

## 5. 今後のロードマップ（Season 3 残り）

### Phase 2: データ品質・キャッシュ（2-3週間）
- Step 3.2-A: バリデーション強化
- Step 3.2-B: リトライ機能統合
- Step 3.2-C: Redisキャッシュ導入
- Step 3.2-D: バッチ処理最適化
- Step 3.2-E: クエリ最適化

### Phase 3: インポート/エクスポート（2-3週間）
- Step 3.3-A: Shapefile/GeoPackageインポート
- Step 3.3-B: エクスポート機能
- Step 3.3-C: タイルセット管理強化
- Step 3.3-D: 履歴・バージョン管理

### Phase 4: エンタープライズ機能（3-4週間）
- Step 3.4-A: チーム/組織管理
- Step 3.4-B: 権限管理
- Step 3.4-C: APIキー管理
- Step 3.4-D: 使用量モニタリング

---

## 6. 技術メモ

### 6.1 Fly.io環境情報

```toml
# fly.toml 主要設定
app = "geo-base-api"
primary_region = "nrt"  # 東京リージョン

[http_service]
  internal_port = 8080
  auto_stop_machines = "stop"
  auto_start_machines = true

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### 6.2 シークレット設定済み（Fly.io API）

```
DATABASE_URL        - Supabase PostgreSQL接続文字列
SUPABASE_URL        - Supabaseエンドポイント
SUPABASE_JWT_SECRET - JWT検証シークレット
ENVIRONMENT         - production
LOG_LEVEL           - INFO
```

### 6.3 Dockerイメージ構成

- ベースイメージ: `ghcr.io/osgeo/gdal:ubuntu-small-3.8.5`
- Python: 3.11
- パッケージ管理: uv
- GDAL: 3.8.5（rasterio, rio-tiler対応）

### 6.4 get_base_url 関数（HTTPS対応済み）

```python
def get_base_url(request: Request) -> str:
    """
    Get base URL from request headers.
    
    Handles various proxy configurations including Fly.io and Vercel.
    Always uses HTTPS in production (non-localhost).
    """
    forwarded_proto = (
        request.headers.get("x-forwarded-proto") or
        request.headers.get("fly-forwarded-proto") or
        "http"
    )
    
    forwarded_host = (
        request.headers.get("x-forwarded-host") or
        request.headers.get("host")
    )
    
    if forwarded_host:
        # Force HTTPS for non-localhost hosts
        if "localhost" not in forwarded_host and "127.0.0.1" not in forwarded_host:
            forwarded_proto = "https"
        return f"{forwarded_proto}://{forwarded_host}"
    
    base_url = str(request.base_url).rstrip("/")
    if base_url.startswith("http://") and "localhost" not in base_url:
        base_url = base_url.replace("http://", "https://", 1)
    
    return base_url
```

---

## 7. 参考リソース

### プロジェクトドキュメント

| ファイル | 説明 |
|---------|------|
| `/mnt/project/ROADMAP_S3.md` | Season 3 完全ロードマップ |
| `/mnt/project/HANDOVER_MAIN_REFACTORING.md` | main.pyリファクタリング完了ドキュメント |
| `/mnt/project/geo-base.txt` | 最新ソースコードスナップショット |
| `/mnt/project/MCP_BEST_PRACTICES.md` | MCPサーバー実装ベストプラクティス |

### 外部ドキュメント

- [Fly.io Documentation](https://fly.io/docs/)
- [rio-tiler Documentation](https://cogeotiff.github.io/rio-tiler/)
- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

---

## 8. 次回作業の開始手順

```fish
# 1. リポジトリを最新に更新
cd /path/to/geo-base
git checkout develop
git pull origin develop

# 2. 新しいブランチを作成（Phase 2用）
git checkout -b feat/s3_phase2_data-quality

# 3. 動作確認
curl https://geo-base-api.fly.dev/api/health
curl https://geo-base-api.fly.dev/api/tilesets

# 4. Step 3.2-A の作業を開始
# - bounds/center計算修正
# - バリデーション強化
```

---

## 9. 成果物まとめ

### 今回のセッションで追加・更新されたファイル

```
api/lib/
├── main.py                 # 更新（4,124行 → 150行）
├── models/                 # 新規作成
│   ├── __init__.py
│   ├── tileset.py
│   ├── feature.py
│   └── datasource.py
├── routers/                # 新規作成
│   ├── __init__.py
│   ├── health.py
│   ├── tilesets.py
│   ├── features.py
│   ├── datasources.py
│   ├── colormaps.py
│   ├── stats.py
│   └── tiles/
│       ├── __init__.py
│       ├── mbtiles.py
│       ├── dynamic.py
│       ├── pmtiles.py
│       └── raster.py
└── README.md               # 更新

HANDOVER_MAIN_REFACTORING.md  # 更新（完了版）
HANDOVER_S3.md                # 新規作成（本ドキュメント）
```

---

**作成者**: Claude (Anthropic)  
**完了日**: 2025-12-17  
**次回作業**: Phase 2 Step 3.2-A（バリデーション強化）
