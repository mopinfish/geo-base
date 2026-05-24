# Step 3: フロントエンド source-layer 修正

## 概要

マッププレビューコンポーネントで、TileJSONの`vector_layers[0].id`を`source-layer`として使用するように修正します。

## 修正対象

**ファイル**: `app/src/components/map/tileset-map-preview.tsx`  
**関数**: `getSourceLayerName`

## 問題の原因

Step 2でTileJSONの`tiles` URLに`layer`パラメータを追加しました。これにより、MVTレイヤー名は`vector_layers[0].id`（例: "preschool"）になります。

しかし、フロントエンドでは`source-layer`として常に`"features"`を使用していたため、レイヤー名が一致せずタイルが表示されません。

## 修正手順

### 1. ファイルを開く

```bash
code app/src/components/map/tileset-map-preview.tsx
```

### 2. `getSourceLayerName`関数を検索

以下のコードを検索してください（約行575-589付近）:

```typescript
  const getSourceLayerName = useCallback((): string => {
    if (tileset.type === "vector") {
      // vectorタイプでlayerパラメータなしの場合、MVTレイヤー名は "features"
      return "features";
    }
    
    if (tileset.type === "pmtiles") {
      const vectorLayers = getVectorLayers();
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
    }
    
    return "default";
  }, [tileset.type, getVectorLayers]);
```

### 3. 以下のコードに置換

```typescript
  /**
   * ソースレイヤー名を決定
   * 
   * vectorタイプ:
   *   - TileJSONのtiles URLにlayerパラメータが含まれるため、
   *     MVT内のレイヤー名はvector_layers[0].idになる
   *   - TileJSONがない場合は "features" にフォールバック
   * 
   * pmtiles:
   *   - TileJSONのvector_layersから取得（PMTilesに含まれるレイヤー名）
   */
  const getSourceLayerName = useCallback((): string => {
    // TileJSONのvector_layersから取得を試みる
    const vectorLayers = getVectorLayers();
    
    if (tileset.type === "vector") {
      // vectorタイプ: TileJSONのvector_layers[0].idを使用
      // TileJSONのtiles URLにlayerパラメータが含まれるため、
      // MVTレイヤー名はそのlayer名になる
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
      // フォールバック: TileJSONがない場合は "features"
      return "features";
    }
    
    if (tileset.type === "pmtiles") {
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
    }
    
    return "default";
  }, [tileset.type, getVectorLayers]);
```

### 4. 変更点のサマリー

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| vectorタイプの`source-layer` | 常に`"features"` | `vector_layers[0].id`を優先使用 |
| フォールバック | なし | `"features"` |

## コミット手順

```fish
cd /path/to/geo-base

git add app/src/components/map/tileset-map-preview.tsx
git commit -m "fix(app): Step 3 - マッププレビューのsource-layer修正

- vectorタイプでTileJSONのvector_layers[0].idを使用
- TileJSONがない場合は'features'にフォールバック
- QGIS互換性の向上"
git push origin develop
```

## テスト項目

- [ ] ベクタータイルセットの詳細ページでマッププレビューが表示される
- [ ] ブラウザコンソールに`source-layer`の値がログ出力される（例: "preschool"）
- [ ] 地図上にフィーチャーが正しく表示される
- [ ] 複数タイルセットで正常に動作する

## 確認方法

1. ブラウザの開発者ツールを開く
2. タイルセット詳細ページにアクセス
3. コンソールで以下のログを確認:
   ```
   [TilesetMapPreview] tileset.type: vector
   [TilesetMapPreview] source-layer: "preschool"
   [TilesetMapPreview] tileUrl: .../api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=xxx&layer=preschool
   ```

`source-layer`の値がTileURLの`layer`パラメータと一致していれば成功です。
