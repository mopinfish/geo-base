# geo-base API Tests

このディレクトリには geo-base API サーバーのテストコードが含まれています。

## テスト構成

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `conftest.py` | - | 共通フィクスチャ（GeoJSON、bounds、center等） |
| `test_validators.py` | 61 | ジオメトリバリデーションテスト |
| `test_tileset_models.py` | 37 | Pydanticモデルテスト |
| `test_fix_bounds.py` | 34 | bounds修正スクリプトテスト |
| `test_retry.py` | 51 | リトライユーティリティテスト |
| `test_db_helpers.py` | 29 | DBヘルパー関数テスト |

**合計**: 212テスト

## テスト実行方法

```fish
cd api

# 全テスト実行
uv run pytest tests/ -v

# 特定テストファイル
uv run pytest tests/test_validators.py -v
uv run pytest tests/test_retry.py -v
uv run pytest tests/test_db_helpers.py -v

# カバレッジ付き
uv run pytest tests/ --cov=lib --cov-report=term-missing

# マーカーでフィルタ（例: 統合テストのみ）
uv run pytest tests/ -v -m integration

# 特定テストクラス
uv run pytest tests/test_retry.py::TestWithDbRetryDecorator -v

# 失敗時に詳細表示
uv run pytest tests/ -v --tb=long
```

## テストカテゴリ

### バリデーションテスト (`test_validators.py`)

- 座標バリデーション（経度・緯度の範囲チェック）
- bounds/centerバリデーション
- GeoJSONジオメトリ構造検証
- Feature/FeatureCollectionバリデーション
- アンチ子午線（日付変更線）対応

### モデルテスト (`test_tileset_models.py`)

- TilesetCreate/TilesetUpdateのPydanticバリデーション
- bounds/center値の正規化
- 型変換とフィールド検証
- min_zoom ≤ max_zoom の検証

### bounds修正テスト (`test_fix_bounds.py`)

- 問題検出ロジック
- bounds/center自動修正
- ドライランモード
- 様々なエッジケース

### リトライテスト (`test_retry.py`)

- `RetryConfig` 設定
- `is_retryable_error` エラー判定
- `calculate_delay` 遅延計算
- `with_retry` / `with_db_retry` デコレータ
- `execute_with_retry` / `execute_db_operation` 実行関数
- `RetryContext` コンテキストマネージャ
- `RetryableOperation` クラス

### DBヘルパーテスト (`test_db_helpers.py`)

- `execute_query` クエリ実行
- `execute_query_with_columns` カラム付きクエリ
- `execute_query_as_dicts` 辞書形式結果
- `execute_transaction` トランザクション
- `execute_insert` / `execute_update` / `execute_delete` CRUD操作
- 便利関数（`get_tileset_by_id`, `check_tileset_owner`, `count_features`）

## 共通フィクスチャ (`conftest.py`)

### GeoJSONジオメトリ

```python
sample_point            # Point型
sample_linestring       # LineString型
sample_polygon          # Polygon型
sample_multipoint       # MultiPoint型
sample_multilinestring  # MultiLineString型
sample_multipolygon     # MultiPolygon型
sample_geometry_collection  # GeometryCollection型
sample_polygon_with_hole    # 穴あきPolygon
```

### Feature/FeatureCollection

```python
sample_feature              # 単一Feature
sample_feature_collection   # FeatureCollection
```

### Bounds/Center

```python
sample_bounds_tokyo      # [139.5, 35.5, 140.0, 36.0]
sample_bounds_world      # [-180, -90, 180, 90]
sample_bounds_antimeridian  # 日付変更線をまたぐbounds
sample_center_tokyo      # [139.75, 35.75]
sample_center_with_zoom  # [139.75, 35.75, 10]
```

### 無効データ（エラーテスト用）

```python
invalid_geometry_no_type
invalid_geometry_bad_type
invalid_bounds_south_greater
invalid_center_out_of_range
```

### リトライテスト用

```python
basic_config    # 基本的なRetryConfig
db_config       # DB用RetryConfig
mock_conn       # モックDB接続
test_config     # 短い遅延のテスト用設定
```

## 環境変数

テスト実行時に以下の環境変数を設定できます：

```fish
# リトライ設定
set -x RETRY_MAX_ATTEMPTS 3
set -x RETRY_BASE_DELAY 0.5
set -x RETRY_MAX_DELAY 10

# ログレベル
set -x LOG_LEVEL DEBUG
```

## CI/CD統合

GitHub Actionsでの実行例：

```yaml
- name: Run Tests
  run: |
    cd api
    uv run pytest tests/ -v --cov=lib --cov-report=xml
```

## 新しいテストの追加

1. `tests/`ディレクトリに`test_*.py`ファイルを作成
2. 共通フィクスチャが必要な場合は`conftest.py`に追加
3. テストクラス名は`Test*`で開始
4. テストメソッド名は`test_*`で開始

例：

```python
import pytest

class TestNewFeature:
    def test_basic_functionality(self, sample_point):
        result = new_function(sample_point)
        assert result is not None
    
    def test_error_handling(self):
        with pytest.raises(ValueError):
            new_function(None)
```

## トラブルシューティング

### ImportError: No module named 'lib'

```fish
# PYTHONPATHを設定
cd api
set -x PYTHONPATH .
uv run pytest tests/ -v
```

### テストが遅い

リトライ関連のテストは意図的に短い遅延を使用しています。
本番環境の設定とは異なります。

### モックの問題

`unittest.mock`のMockやMagicMockを使用する際は、
コンテキストマネージャ(`__enter__`, `__exit__`)の設定に注意。

---

**最終更新**: 2025-12-17  
**テスト総数**: 212
