# geo-base API Tests

このディレクトリには geo-base API のユニットテストが含まれています。

## テスト構成

```
api/tests/
├── __init__.py           # テストモジュール初期化
├── conftest.py           # 共通フィクスチャ・設定
├── test_validators.py    # バリデーションユーティリティテスト
├── test_tileset_models.py # Pydanticモデルテスト
└── test_fix_bounds.py    # bounds修正スクリプトテスト
```

## テスト実行方法

### 全テスト実行

```bash
cd api
uv run pytest tests/ -v
```

### 特定のテストファイルを実行

```bash
# バリデーションテスト
uv run pytest tests/test_validators.py -v

# モデルテスト
uv run pytest tests/test_tileset_models.py -v

# bounds修正スクリプトテスト
uv run pytest tests/test_fix_bounds.py -v
```

### カバレッジレポート付き

```bash
uv run pytest tests/ --cov=lib --cov-report=term-missing
```

### 特定のテストクラスを実行

```bash
uv run pytest tests/test_validators.py::TestGeometryValidation -v
```

### 特定のテストメソッドを実行

```bash
uv run pytest tests/test_validators.py::TestGeometryValidation::test_valid_point -v
```

## テスト内容

### test_validators.py (61テスト)

`lib/validators.py` のジオメトリ・データバリデーション機能をテスト。

- `TestValidationResult` - ValidationResultクラスのテスト
- `TestCoordinateValidation` - 座標バリデーション（経度・緯度）
- `TestBoundsValidation` - bounding box バリデーション
- `TestCenterValidation` - center point バリデーション
- `TestGeometryValidation` - GeoJSONジオメトリバリデーション
- `TestFeatureValidation` - GeoJSON Feature バリデーション
- `TestFeatureCollectionValidation` - FeatureCollection バリデーション
- `TestBatchValidation` - 一括バリデーション
- `TestConvenienceFunctions` - 便利関数のテスト

### test_tileset_models.py (37テスト)

`lib/models/tileset.py` のPydanticモデルをテスト。

- `TestBoundsValidation` - bounds値バリデーションヘルパー
- `TestCenterValidation` - center値バリデーションヘルパー
- `TestTilesetCreate` - タイルセット作成モデル
- `TestTilesetUpdate` - タイルセット更新モデル
- `TestTilesetResponse` - タイルセットレスポンスモデル

### test_fix_bounds.py (34テスト)

`scripts/fix_bounds.py` のバリデーション・データ処理をテスト。

- `TestValidateBounds` - bounds バリデーション
- `TestValidateCenter` - center バリデーション
- `TestIsCenterInBounds` - center-in-bounds チェック
- `TestBoundsIssue` - BoundsIssue データクラス
- `TestFixResult` - FixResult データクラス
- `TestScanReport` - ScanReport データクラス
- `TestDatabaseIntegration` - データベース統合テスト（スキップ）

## 共通フィクスチャ (conftest.py)

### GeoJSONフィクスチャ

- `sample_point` - Point ジオメトリ
- `sample_linestring` - LineString ジオメトリ
- `sample_polygon` - Polygon ジオメトリ
- `sample_polygon_with_hole` - 穴付きPolygon
- `sample_multipoint` - MultiPoint
- `sample_multilinestring` - MultiLineString
- `sample_multipolygon` - MultiPolygon
- `sample_geometry_collection` - GeometryCollection
- `sample_feature` - GeoJSON Feature
- `sample_feature_collection` - FeatureCollection

### Bounds/Centerフィクスチャ

- `sample_bounds_tokyo` - 東京エリアのbounds
- `sample_bounds_world` - 世界全体のbounds
- `sample_bounds_antimeridian` - 日付変更線をまたぐbounds
- `sample_center_tokyo` - 東京のcenter
- `sample_center_with_zoom` - zoom付きcenter

### 無効データフィクスチャ（エラーテスト用）

- `invalid_geometry_no_type` - type無しジオメトリ
- `invalid_geometry_bad_type` - 不正なtype
- `invalid_geometry_no_coords` - coordinates無し
- `invalid_point_out_of_range` - 範囲外座標
- `invalid_polygon_not_closed` - 閉じていないPolygon
- `invalid_bounds_south_greater` - south > north
- `invalid_center_out_of_range` - 範囲外center

### データベースフィクスチャ

- `database_url` - DATABASE_URL環境変数から取得
- `db_connection` - データベース接続（自動ロールバック）

## 環境変数

一部のテスト（データベース統合テスト）では以下の環境変数が必要です：

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

環境変数が設定されていない場合、該当テストはスキップされます。

## テスト追加のガイドライン

1. **フィクスチャを活用** - `conftest.py` の共通フィクスチャを使用
2. **クラスでグループ化** - 関連テストは `Test*` クラスにまとめる
3. **明確な命名** - `test_<機能>_<状況>` の形式
4. **docstring追加** - 各テストに簡潔な説明を追加
5. **エッジケース** - 境界値、エラーケースもテスト
