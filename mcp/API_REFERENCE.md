# geo-base MCP Server API Reference

このドキュメントは、geo-base MCP サーバーで利用可能なすべてのツールの詳細なAPI仕様を提供します。

## 目次

1. [タイルセットツール](#タイルセットツール)
2. [フィーチャーツール](#フィーチャーツール)
3. [ジオコーディングツール](#ジオコーディングツール)
4. [統計ツール](#統計ツール)
5. [空間分析ツール](#空間分析ツール)
6. [CRUD ツール](#crud-ツール)
7. [ユーティリティツール](#ユーティリティツール)
8. [エラーレスポンス](#エラーレスポンス)

---

## タイルセットツール

### `list_tilesets`

タイルサーバーから利用可能なタイルセット一覧を取得します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `type` | string | No | null | タイルセットタイプでフィルタ (`vector`, `raster`, `pmtiles`) |
| `is_public` | boolean | No | null | 公開/非公開ステータスでフィルタ |

#### レスポンス

```json
{
  "tilesets": [
    {
      "id": "uuid",
      "name": "タイルセット名",
      "description": "説明",
      "type": "vector",
      "format": "pbf",
      "min_zoom": 0,
      "max_zoom": 22,
      "is_public": true
    }
  ],
  "count": 1
}
```

---

### `get_tileset`

特定のタイルセットの詳細情報を取得します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | タイルセットのUUID |

#### レスポンス

```json
{
  "id": "uuid",
  "name": "タイルセット名",
  "description": "説明",
  "type": "vector",
  "format": "pbf",
  "min_zoom": 0,
  "max_zoom": 22,
  "bounds": [-180, -90, 180, 90],
  "center": [139.7671, 35.6812],
  "attribution": "© OpenStreetMap",
  "is_public": true,
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### `get_tileset_tilejson`

タイルセットのTileJSONメタデータを取得します。MapLibre GL JSなどのマップクライアントとの連携に使用します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | タイルセットのUUID |

#### レスポンス

```json
{
  "tilejson": "3.0.0",
  "tiles": ["https://example.com/api/tilesets/{id}/tiles/{z}/{x}/{y}.pbf"],
  "bounds": [-180, -90, 180, 90],
  "minzoom": 0,
  "maxzoom": 22,
  "vector_layers": [
    {
      "id": "default",
      "fields": {}
    }
  ]
}
```

---

## フィーチャーツール

### `search_features`

地理フィーチャーを検索します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `bbox` | string | No | null | バウンディングボックス `"minx,miny,maxx,maxy"` (WGS84) |
| `layer` | string | No | null | レイヤー名フィルター |
| `filter` | string | No | null | プロパティフィルター `"key=value"` |
| `limit` | integer | No | 100 | 返すフィーチャーの最大数 (1-1000) |
| `tileset_id` | string (UUID) | No | null | 特定のタイルセットに限定 |

#### レスポンス

```json
{
  "features": [
    {
      "id": "uuid",
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [139.7671, 35.6812]
      },
      "properties": {
        "name": "東京駅"
      },
      "layer": "stations",
      "tileset_id": "uuid"
    }
  ],
  "count": 1,
  "query": {
    "bbox": "139.5,35.5,140.0,36.0",
    "layer": null,
    "filter": null,
    "tileset_id": null,
    "limit": 100
  }
}
```

---

### `get_feature`

特定のフィーチャーの詳細情報を取得します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `feature_id` | string (UUID) | Yes | フィーチャーのUUID |

#### レスポンス

```json
{
  "id": "uuid",
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [139.7671, 35.6812]
  },
  "geometry_summary": {
    "type": "Point",
    "coordinate_count": 1
  },
  "properties": {
    "name": "東京駅"
  },
  "layer": "stations",
  "tileset_id": "uuid",
  "tileset_name": "東京の駅",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### `get_features_in_tile`

特定のマップタイル内のフィーチャーを取得します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `tileset_id` | string (UUID) | Yes | - | タイルセットのUUID |
| `z` | integer | Yes | - | ズームレベル (0-22) |
| `x` | integer | Yes | - | タイルX座標 |
| `y` | integer | Yes | - | タイルY座標 |
| `layer` | string | No | null | レイヤー名フィルター |

#### レスポンス

```json
{
  "features": [...],
  "count": 10,
  "tile": {
    "z": 14,
    "x": 14370,
    "y": 6450,
    "tileset_id": "uuid"
  },
  "tile_bounds": {
    "min_lng": 139.7,
    "min_lat": 35.6,
    "max_lng": 139.8,
    "max_lat": 35.7
  }
}
```

---

## ジオコーディングツール

### `geocode`

住所または地名を地理座標に変換します。OpenStreetMap Nominatim APIを使用します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `query` | string | Yes | - | 検索する住所または地名 |
| `limit` | integer | No | 5 | 最大結果数 (1-50) |
| `country_codes` | string | No | null | ISO 3166-1 国コード（カンマ区切り） |
| `language` | string | No | "ja" | 結果の言語 |

#### レスポンス

```json
{
  "results": [
    {
      "name": "東京駅, 丸の内, 千代田区, 東京都, 日本",
      "latitude": 35.6812,
      "longitude": 139.7671,
      "type": "station",
      "category": "railway",
      "importance": 0.85,
      "place_id": 123456,
      "osm_type": "node",
      "osm_id": 7890,
      "address": {
        "country": "日本",
        "city": "千代田区",
        "road": "丸の内"
      },
      "bounds": {
        "south": 35.68,
        "north": 35.69,
        "west": 139.76,
        "east": 139.77
      }
    }
  ],
  "count": 1,
  "query": "東京駅"
}
```

---

### `reverse_geocode`

地理座標を住所に変換します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `latitude` | float | Yes | - | 緯度 (-90〜90) |
| `longitude` | float | Yes | - | 経度 (-180〜180) |
| `zoom` | integer | No | 18 | 詳細レベル (0-18) |
| `language` | string | No | "ja" | 結果の言語 |

**ズームレベルの目安:**
- 0: 国レベル
- 10: 市区町村レベル
- 14: 地区レベル
- 16: 道路レベル
- 18: 建物レベル

#### レスポンス

```json
{
  "display_name": "東京駅, 丸の内, 千代田区, 東京都, 日本",
  "coordinates": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "type": "station",
  "category": "railway",
  "place_id": 123456,
  "osm_type": "node",
  "osm_id": 7890,
  "address": {
    "country": "日本",
    "city": "千代田区",
    "road": "丸の内"
  },
  "bounds": {
    "south": 35.68,
    "north": 35.69,
    "west": 139.76,
    "east": 139.77
  }
}
```

---

## 統計ツール

### `get_tileset_stats`

タイルセットの包括的な統計情報を取得します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | タイルセットのUUID |

#### レスポンス

```json
{
  "tileset_id": "uuid",
  "tileset_name": "タイルセット名",
  "tileset_type": "vector",
  "feature_count": 150,
  "geometry_types": {
    "Point": 100,
    "LineString": 30,
    "Polygon": 20
  },
  "layers": {
    "stations": {
      "feature_count": 100,
      "geometry_types": {"Point": 100}
    },
    "routes": {
      "feature_count": 50,
      "geometry_types": {"LineString": 30, "Polygon": 20}
    }
  },
  "coordinate_count": 5000,
  "bounds": [-180, -90, 180, 90],
  "zoom_range": {"min": 0, "max": 22},
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_feature_distribution`

フィーチャーのジオメトリタイプ分布を取得します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `tileset_id` | string (UUID) | No | null | 特定のタイルセットに限定 |
| `bbox` | string | No | null | バウンディングボックス `"minx,miny,maxx,maxy"` |

#### レスポンス

```json
{
  "total_features": 150,
  "geometry_types": {
    "Point": 100,
    "LineString": 30,
    "Polygon": 20
  },
  "percentages": {
    "Point": 66.67,
    "LineString": 20.0,
    "Polygon": 13.33
  },
  "query": {
    "tileset_id": "uuid",
    "bbox": null
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_layer_stats`

レイヤー別の統計情報を取得します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | タイルセットのUUID |

#### レスポンス

```json
{
  "tileset_id": "uuid",
  "total_features": 150,
  "layer_count": 3,
  "layers": {
    "stations": {
      "feature_count": 100,
      "geometry_types": {"Point": 100},
      "percentage": 66.67,
      "property_keys": ["name", "type", "passengers"]
    },
    "routes": {
      "feature_count": 50,
      "geometry_types": {"LineString": 50},
      "percentage": 33.33,
      "property_keys": ["name", "length"]
    }
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_area_stats`

指定エリアの統計情報を取得します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `bbox` | string | Yes | - | バウンディングボックス `"minx,miny,maxx,maxy"` |
| `tileset_id` | string (UUID) | No | null | 特定のタイルセットに限定 |

#### レスポンス

```json
{
  "bbox": {
    "min_lng": 139.5,
    "min_lat": 35.5,
    "max_lng": 140.0,
    "max_lat": 36.0
  },
  "area_km2": 2500.0,
  "feature_count": 150,
  "density": {
    "features_per_km2": 0.06,
    "features_per_100km2": 6.0
  },
  "geometry_types": {
    "Point": 100,
    "LineString": 50
  },
  "layers": ["stations", "routes"],
  "tilesets_found": 2,
  "query": {
    "bbox": "139.5,35.5,140.0,36.0",
    "tileset_id": null
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

## 空間分析ツール

### `analyze_area`

指定エリアの包括的な空間分析を実行します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `bbox` | string | Yes | - | バウンディングボックス `"minx,miny,maxx,maxy"` |
| `tileset_id` | string (UUID) | No | null | 特定のタイルセットに限定 |
| `include_density` | boolean | No | true | 密度分析を含める |
| `include_clustering` | boolean | No | true | クラスタリング分析を含める |

#### レスポンス

```json
{
  "bbox": {
    "min_lng": 139.5,
    "min_lat": 35.5,
    "max_lng": 140.0,
    "max_lat": 36.0
  },
  "area_km2": 2500.0,
  "features": {
    "count": 150,
    "geometry_types": {"Point": 100, "LineString": 50}
  },
  "density": {
    "features_per_km2": 0.06,
    "grid": {
      "size": "3x3",
      "cells": [[10, 20, 15], [25, 30, 20], [10, 15, 5]]
    },
    "hotspots": [
      {"lat": 35.75, "lng": 139.75, "count": 30}
    ]
  },
  "clustering": {
    "threshold_km": 5.0,
    "cluster_count": 5,
    "top_clusters": [
      {"center": {"lat": 35.7, "lng": 139.7}, "member_count": 25}
    ],
    "isolated_features": 10
  },
  "layers": {"stations": 100, "routes": 50},
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `calculate_distance`

2点間の距離を計算します（ハバーサイン公式）。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `lat1` | float | Yes | 始点の緯度 |
| `lng1` | float | Yes | 始点の経度 |
| `lat2` | float | Yes | 終点の緯度 |
| `lng2` | float | Yes | 終点の経度 |

#### レスポンス

```json
{
  "distance_km": 15.5,
  "distance_m": 15500,
  "distance_miles": 9.63,
  "bearing": 45.0,
  "bearing_direction": "NE",
  "points": {
    "start": {"latitude": 35.6812, "longitude": 139.7671},
    "end": {"latitude": 35.6580, "longitude": 139.7016}
  }
}
```

---

### `find_nearest_features`

指定地点の近傍フィーチャーを検索します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `lat` | float | Yes | - | 検索中心の緯度 |
| `lng` | float | Yes | - | 検索中心の経度 |
| `radius_km` | float | No | 1.0 | 検索半径（km） |
| `limit` | integer | No | 10 | 最大結果数 (1-100) |
| `tileset_id` | string (UUID) | No | null | 特定のタイルセットに限定 |
| `layer` | string | No | null | レイヤー名フィルター |

#### レスポンス

```json
{
  "center": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "radius_km": 1.0,
  "features": [
    {
      "id": "uuid",
      "type": "Feature",
      "geometry": {...},
      "properties": {"name": "東京駅"},
      "distance_km": 0.15,
      "distance_m": 150
    }
  ],
  "count": 5
}
```

---

### `get_buffer_zone_features`

リングバッファ（ドーナツ形状）内のフィーチャーを取得します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `lat` | float | Yes | 中心点の緯度 |
| `lng` | float | Yes | 中心点の経度 |
| `inner_radius_km` | float | Yes | 内側の半径（km） |
| `outer_radius_km` | float | Yes | 外側の半径（km） |
| `tileset_id` | string (UUID) | No | 特定のタイルセットに限定 |

#### レスポンス

```json
{
  "center": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "inner_radius_km": 1.0,
  "outer_radius_km": 2.0,
  "ring_area_km2": 9.42,
  "features": [...],
  "count": 15,
  "density_per_km2": 1.59
}
```

---

## CRUD ツール

> **注意:** すべてのCRUDツールは認証が必要です。有効なJWTトークンを `API_TOKEN` 環境変数に設定してください。

### `create_tileset`

新しいタイルセットを作成します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `name` | string | Yes | - | タイルセット名 |
| `type` | string | Yes | - | タイプ (`vector`, `raster`, `pmtiles`) |
| `format` | string | Yes | - | フォーマット (`pbf`, `png`, `jpg`, `webp`, `geojson`) |
| `description` | string | No | null | 説明 |
| `min_zoom` | integer | No | 0 | 最小ズームレベル (0-22) |
| `max_zoom` | integer | No | 22 | 最大ズームレベル (0-22) |
| `bounds` | array | No | null | バウンディングボックス [west, south, east, north] |
| `center` | array | No | null | 中心点 [longitude, latitude] |
| `attribution` | string | No | null | 帰属テキスト |
| `is_public` | boolean | No | false | 公開設定 |
| `metadata` | object | No | null | 追加メタデータ |

#### レスポンス

```json
{
  "id": "uuid",
  "name": "タイルセット名",
  "type": "vector",
  "format": "pbf",
  ...
}
```

---

### `update_tileset`

既存のタイルセットを更新します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | 更新するタイルセットのUUID |
| その他 | - | No | `create_tileset` と同じ（指定されたフィールドのみ更新） |

---

### `delete_tileset`

タイルセットとそのすべてのフィーチャーを削除します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `tileset_id` | string (UUID) | Yes | 削除するタイルセットのUUID |

#### レスポンス

```json
{
  "success": true,
  "message": "Tileset {uuid} deleted successfully."
}
```

---

### `create_feature`

タイルセットに新しいフィーチャーを作成します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `tileset_id` | string (UUID) | Yes | - | 親タイルセットのUUID |
| `geometry` | object | Yes | - | GeoJSONジオメトリオブジェクト |
| `properties` | object | No | null | フィーチャープロパティ |
| `layer_name` | string | No | "default" | レイヤー名 |

#### ジオメトリの例

```json
// Point
{"type": "Point", "coordinates": [139.7671, 35.6812]}

// LineString
{"type": "LineString", "coordinates": [[139.7, 35.6], [139.8, 35.7]]}

// Polygon
{"type": "Polygon", "coordinates": [[[139.7, 35.6], [139.8, 35.6], [139.8, 35.7], [139.7, 35.7], [139.7, 35.6]]]}
```

---

### `update_feature`

既存のフィーチャーを更新します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `feature_id` | string (UUID) | Yes | 更新するフィーチャーのUUID |
| `geometry` | object | No | 新しいジオメトリ |
| `properties` | object | No | 新しいプロパティ（既存のすべてを置換） |
| `layer_name` | string | No | 新しいレイヤー名 |

---

### `delete_feature`

フィーチャーを削除します。

#### パラメータ

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `feature_id` | string (UUID) | Yes | 削除するフィーチャーのUUID |

---

## ユーティリティツール

### `get_tile_url`

特定のマップタイルのURLを生成します。

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|----------|------|
| `tileset_id` | string (UUID) | Yes | - | タイルセットのUUID |
| `z` | integer | Yes | - | ズームレベル (0-22) |
| `x` | integer | Yes | - | タイルX座標 |
| `y` | integer | Yes | - | タイルY座標 |
| `format` | string | No | "pbf" | タイルフォーマット (`pbf`, `png`, `jpg`, `webp`) |

#### レスポンス

```json
{
  "url": "https://example.com/api/tilesets/{id}/tiles/14/14370/6450.pbf",
  "tileset_id": "uuid",
  "coordinates": {"z": 14, "x": 14370, "y": 6450},
  "format": "pbf"
}
```

---

### `health_check`

タイルサーバーのヘルスステータスを確認します。

#### パラメータ

なし

#### レスポンス

```json
{
  "status": "healthy",
  "database": "ok",
  "pmtiles": "ok",
  "rasterio": "unavailable"
}
```

---

### `get_server_info`

MCPサーバーの設定情報を取得します。

#### パラメータ

なし

#### レスポンス

```json
{
  "tile_server_url": "https://geo-base-api.fly.dev",
  "mcp_server_name": "geo-base",
  "mcp_server_version": "1.0.0",
  "environment": "production"
}
```

---

## エラーレスポンス

すべてのツールは、エラー発生時に以下の形式でレスポンスを返します：

```json
{
  "error": "エラーメッセージ",
  "code": "ERROR_CODE",
  "hint": "問題解決のヒント（オプション）",
  "detail": "追加の詳細情報（オプション）"
}
```

### エラーコード一覧

| コード | 説明 |
|--------|------|
| `VALIDATION_ERROR` | 入力パラメータが無効 |
| `NOT_FOUND` | リソースが見つからない |
| `UNAUTHORIZED` | 認証が必要 |
| `FORBIDDEN` | アクセス権限がない |
| `HTTP_ERROR` | HTTPエラー（4xx/5xx） |
| `NETWORK_ERROR` | ネットワークエラー |
| `UNKNOWN_ERROR` | 予期しないエラー |

### 例

```json
{
  "error": "Invalid tileset_id format. Expected UUID.",
  "code": "VALIDATION_ERROR",
  "tileset_id": "invalid-id"
}
```

```json
{
  "error": "Feature not found",
  "code": "NOT_FOUND",
  "feature_id": "00000000-0000-0000-0000-000000000000"
}
```

```json
{
  "error": "Authentication required",
  "code": "UNAUTHORIZED",
  "hint": "This feature may belong to a private tileset. Configure API_TOKEN."
}
```
