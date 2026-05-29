# Step 2: TileJSON vector_layers修正

## 概要

TileJSONの`tiles` URLに`layer`パラメータを追加し、`vector_layers[].id`とMVTレイヤー名を一致させます。

## 修正対象

**ファイル**: `api/lib/main.py`  
**関数**: `get_tileset_tilejson`  
**修正箇所**: 行4258-4276付近

## 問題の原因

```
修正前:
  TileJSON:  vector_layers[].id = "imported" (DBのlayer_name)
  tiles URL: .../features/{z}/{x}/{y}.pbf?tileset_id=xxx （layerパラメータなし）
  MVT:       layer = "features" (デフォルト)
  → 不一致 → QGISエラー

修正後:
  TileJSON:  vector_layers[].id = "imported"
  tiles URL: .../features/{z}/{x}/{y}.pbf?tileset_id=xxx&layer=imported
  MVT:       layer = "imported" (layerパラメータから)
  → 一致 → QGIS OK
```

## 修正手順

### 方法1: 手動で編集

`api/lib/main.py`を開き、以下の箇所を探して置換してください。

**検索する文字列** (行4258-4276):
```python
            # If no layers found, add a default layer
            if not vector_layers:
                vector_layers.append({
                    "id": "default",
                    "fields": {},
                    "minzoom": min_zoom or 0,
                    "maxzoom": max_zoom or 22,
                    "description": ""
                })
            
            # Build TileJSON response
            tilejson = {
                "tilejson": "3.0.0",
                "name": name,
                "tiles": [f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"],
                "minzoom": min_zoom or 0,
                "maxzoom": max_zoom or 22,
                "vector_layers": vector_layers,
            }
```

**置換後の文字列**:
```python
            # If no layers found, add a default layer
            if not vector_layers:
                layer_names = ["default"]
                vector_layers.append({
                    "id": "default",
                    "fields": {},
                    "minzoom": min_zoom or 0,
                    "maxzoom": max_zoom or 22,
                    "description": ""
                })
            
            # Build tiles URL with layer parameter
            # This ensures MVT layer name matches vector_layers[].id
            if len(layer_names) == 1:
                # Single layer: add layer parameter to match vector_layers[].id
                primary_layer = layer_names[0]
                tiles_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}&layer={primary_layer}"
            else:
                # Multiple layers: currently use first layer
                # TODO: Implement multi-layer MVT generation for full support
                # For now, we use the first layer to ensure QGIS compatibility
                primary_layer = layer_names[0]
                tiles_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}&layer={primary_layer}"
                # Note: Only the first layer will be rendered.
                # Full multi-layer support requires generate_multi_layer_mvt()
            
            # Build TileJSON response
            tilejson = {
                "tilejson": "3.0.0",
                "name": name,
                "tiles": [tiles_url],
                "minzoom": min_zoom or 0,
                "maxzoom": max_zoom or 22,
                "vector_layers": vector_layers,
            }
```

### 方法2: sedコマンドで置換（fish shell）

```fish
cd /path/to/geo-base

# バックアップ作成
cp api/lib/main.py api/lib/main.py.bak

# 置換実行（手動編集を推奨）
```

## コミット手順

```fish
cd /path/to/geo-base

git add api/lib/main.py
git commit -m "fix(api): Step 2 - TileJSON vector_layers修正

- tiles URLにlayerパラメータを追加
- vector_layers[].idとMVTレイヤー名の一致を保証
- QGIS互換性の向上"
git push origin develop
```

## テスト項目

- [ ] TileJSON APIレスポンスで`tiles` URLに`layer`パラメータが含まれること
- [ ] QGISでTileJSON URLを指定して接続できること
- [ ] マッププレビューでタイルが正しく表示されること
- [ ] 単一レイヤーのタイルセットが正常に動作すること

## 確認用curlコマンド

```bash
# TileJSONを取得して確認
curl -s "https://your-domain/api/tilesets/{tileset_id}/tilejson.json" | jq '.tiles[0]'

# 期待される出力例:
# "https://your-domain/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=xxx&layer=imported"
```

## 注意事項

- 複数レイヤーを持つタイルセットでは、現在最初のレイヤーのみが表示されます
- 完全な複数レイヤー対応にはフェーズ2の実装が必要です
