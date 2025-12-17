# geo-base Season 3 引き継ぎドキュメント

**更新日**: 2025-12-17  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**現在のブランチ**: `develop`

---

## 1. 現在のシステム状況

### 1.1 デプロイ状況

| コンポーネント | ステータス | URL | バージョン |
|---------------|-----------|-----|-----------|
| API Server (Fly.io) | ✅ 稼働中 | https://geo-base-api.fly.dev | 0.4.0 → **0.4.1** |
| MCP Server (Fly.io) | ✅ 稼働中 | https://geo-base-mcp.fly.dev | 0.2.5 |
| Admin UI (Vercel) | ✅ 稼働中 | https://geo-base-admin.vercel.app | 0.4.0 |

> **Note**: Vercel版API（geo-base-puce.vercel.app）は廃止済み。すべてのコンポーネントがFly.io APIを参照。

### 1.2 Season 3 進捗サマリー

| フェーズ | ステップ | 内容 | ステータス |
|---------|---------|------|-----------|
| Phase 1 | Step 3.1-A | Fly.io移行準備（Dockerfile, fly.toml） | ✅ 完了 |
| Phase 1 | Step 3.1-B | API移行・動作確認 | ✅ 完了 |
| Phase 1 | Step 3.1-C | COGサポート | ✅ 完了 |
| Phase 1 | Step 3.1-D | ラスター分析 | ✅ 完了 |
| Phase 1 | Step 3.1-E | Admin UI更新 | ✅ 完了 |
| - | main.pyリファクタリング | 4,124行 → 150行にモジュール分割 | ✅ 完了 |
| **Phase 2** | **Step 3.2-A** | **バリデーション強化** | ✅ **完了** |
| Phase 2 | Step 3.2-B | リトライ機能統合 | 🔜 次のステップ |
| Phase 2 | Step 3.2-C | Redisキャッシュ導入 | 📋 計画中 |
| Phase 2 | Step 3.2-D | バッチ処理最適化 | 📋 計画中 |

---

## 2. 今回完了した作業: Step 3.2-A バリデーション強化

### 2.1 概要

bounds/center計算の改善とジオメトリバリデーション機能を実装しました。

### 2.2 実装内容

#### Step 3.2-A.1: ジオメトリバリデーションユーティリティ

**新規ファイル**: `api/lib/validators.py` (~650行)

- `ValidationResult` データクラス（エラー・警告の追跡）
- 座標バリデーション: `validate_longitude`, `validate_latitude`, `validate_coordinate_pair`
- Bounds/Center: `validate_bounds`, `validate_center`（アンチ子午線対応）
- GeoJSONジオメトリ: `validate_geometry`（全タイプ対応）
- Feature/FeatureCollection: `validate_feature`, `validate_feature_collection`
- PostGIS統合: `validate_geometry_with_postgis`, `calculate_bounds_from_geometry`
- バッチ処理: `validate_features_batch`
- 便利関数: `is_valid_geometry`, `normalize_bounds`, `normalize_center`

#### Step 3.2-A.2: bulk import時の自動bounds計算

**更新ファイル**: `api/lib/routers/features.py` (~590行)

- bulk import完了後にタイルセットのbounds/centerを自動計算
- `update_bounds=true`（デフォルト）で有効
- バリデーション統合（`validate_geometry=true`）
- レスポンスに計算後のbounds/center値を含む

**更新ファイル**: `api/lib/models/feature.py` (~65行)

- `BulkFeatureCreate`: `update_bounds`, `validate_geometry`フラグ追加
- `BulkFeatureResponse`: `bounds`, `center`, `warnings`, `bounds_updated`追加

#### Step 3.2-A.3: bounds/centerのPydanticバリデーション

**更新ファイル**: `api/lib/models/tileset.py` (~310行)

- `validate_bounds_values`, `validate_center_values`ヘルパー関数
- `TilesetCreate`: Pydantic `field_validator`でbounds/center検証
- `TilesetUpdate`: 同様のバリデーション
- `TilesetResponse`: 新規追加（将来のAPI型安全性向上用）
- 座標範囲チェック（-180〜180, -90〜90）
- min_zoom ≤ max_zoom の検証
- type/formatの大文字小文字正規化

#### Step 3.2-A.4: 既存データ修正スクリプト

**新規ファイル**: `scripts/fix_bounds.py` (~520行)

```
機能:
- 全タイルセットのスキャン
- bounds/center異常値の検出
- vectorタイルセットの自動修正（featuresから再計算）
- ドライランモードで安全にプレビュー
- 特定タイルセットのみ修正可能

検出する問題:
- invalid_bounds: 範囲外の座標値
- invalid_center: 範囲外のcenter値
- center_outside_bounds: centerがbounds外
- missing_bounds: boundsがない（features有り）
- missing_center: centerがない（features有り）
- bounds_mismatch: 計算値と保存値の差異
- empty_tileset_with_bounds: boundsあるがfeatures無し
```

### 2.3 テストコード

**新規ディレクトリ**: `api/tests/`

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `conftest.py` | - | 共通フィクスチャ（GeoJSON、bounds、center等） |
| `test_validators.py` | 61 | バリデーションユーティリティテスト |
| `test_tileset_models.py` | 37 | Pydanticモデルテスト |
| `test_fix_bounds.py` | 34 | スクリプトテスト |
| `README.md` | - | テストドキュメント |

**テスト結果**:
```
132 passed, 1 skipped in 0.52s
```

### 2.4 追加・更新ファイル一覧

```
api/
├── lib/
│   ├── validators.py           # 新規 (650行)
│   ├── models/
│   │   ├── __init__.py         # 更新
│   │   ├── datasource.py       # 既存
│   │   ├── feature.py          # 更新 (65行)
│   │   └── tileset.py          # 更新 (310行)
│   └── routers/
│       └── features.py         # 更新 (590行)
├── tests/
│   ├── __init__.py             # 新規
│   ├── conftest.py             # 新規 (280行)
│   ├── test_validators.py      # 新規 (380行)
│   ├── test_tileset_models.py  # 新規 (240行)
│   ├── test_fix_bounds.py      # 新規 (220行)
│   └── README.md               # 新規
└── pyproject.toml              # 更新 (pytest設定追加, version 0.4.1)

scripts/
└── fix_bounds.py               # 新規 (520行)
```

---

## 3. APIレスポンスの変更点

### POST /api/features/bulk

リクエストに新しいオプションが追加:

```json
{
  "tileset_id": "uuid",
  "layer_name": "default",
  "features": [...],
  "update_bounds": true,      // 新規: 自動bounds計算
  "validate_geometry": true   // 新規: ジオメトリ検証
}
```

レスポンスに新しいフィールドが追加:

```json
{
  "success_count": 100,
  "failed_count": 2,
  "feature_ids": ["uuid1", "uuid2", ...],
  "errors": ["Feature #5: Invalid geometry: ..."],
  "warnings": ["Feature #3: Polygon exterior ring is not closed"],  // 新規
  "bounds_updated": true,                                           // 新規
  "bounds": [139.5, 35.5, 140.0, 36.0],                            // 新規
  "center": [139.75, 35.75]                                         // 新規
}
```

---

## 4. 次のステップ: Step 3.2-B リトライ機能統合

### 4.1 タスク一覧

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| tilesets.py統合 | retry.pyの関数を適用 | 0.5日 |
| features.py統合 | retry.pyの関数を適用 | 0.5日 |
| API層リトライ | FastAPIレベルでのリトライ | 1日 |
| テスト追加 | リトライシナリオのテスト | 0.5日 |

### 4.2 参考: 既存のリトライ実装

MCPサーバーには既に `mcp/lib/retry.py` が実装済み:

```python
# mcp/lib/retry.py の主要関数
- with_retry(): デコレータ形式のリトライ
- execute_with_retry(): 関数実行のリトライラッパー
- RetryConfig: リトライ設定（max_attempts, delay, backoff等）
```

API側でも同様のパターンを適用予定。

---

## 5. 今後のロードマップ（Phase 2 残り）

### Phase 2: データ品質・キャッシュ（残り2-3週間）

| ステップ | 内容 | ステータス |
|---------|------|-----------|
| Step 3.2-A | バリデーション強化 | ✅ 完了 |
| Step 3.2-B | リトライ機能統合 | 🔜 次 |
| Step 3.2-C | Redisキャッシュ導入 | 📋 計画中 |
| Step 3.2-D | バッチ処理最適化 | 📋 計画中 |
| Step 3.2-E | クエリ最適化 | 📋 計画中 |

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

### 6.1 テスト実行方法

```fish
cd api

# 全テスト実行
uv run pytest tests/ -v

# 特定テストファイル
uv run pytest tests/test_validators.py -v

# カバレッジ付き
uv run pytest tests/ --cov=lib --cov-report=term-missing
```

### 6.2 fix_bounds.py 使用方法

```fish
# 環境変数設定
set -x DATABASE_URL "postgresql://user:pass@host:5432/dbname"

# ドライラン（プレビュー）
python scripts/fix_bounds.py --dry-run --verbose

# 実際に修正
python scripts/fix_bounds.py --verbose

# 特定タイルセットのみ
python scripts/fix_bounds.py --tileset-id <uuid> --verbose

# スキャンのみ
python scripts/fix_bounds.py --scan-only --verbose
```

### 6.3 conftest.py の主なフィクスチャ

```python
# GeoJSONジオメトリ
sample_point, sample_linestring, sample_polygon
sample_multipoint, sample_multilinestring, sample_multipolygon
sample_geometry_collection, sample_polygon_with_hole

# Feature/FeatureCollection
sample_feature, sample_feature_collection

# Bounds/Center
sample_bounds_tokyo      # [139.5, 35.5, 140.0, 36.0]
sample_bounds_world      # [-180, -90, 180, 90]
sample_bounds_antimeridian  # 日付変更線をまたぐ
sample_center_tokyo      # [139.75, 35.75]
sample_center_with_zoom  # [139.75, 35.75, 10]

# 無効データ（エラーテスト用）
invalid_geometry_no_type, invalid_geometry_bad_type
invalid_bounds_south_greater, invalid_center_out_of_range
```

---

## 7. デプロイ手順（今回の変更を適用）

```fish
cd /path/to/geo-base

# zipを解凍して上書き
unzip -o ~/Downloads/geo-base-step3.2-A.zip -d .

# テスト実行確認
cd api
uv run pytest tests/ -v

# コミット & プッシュ
cd ..
git add .
git commit -m "feat(api): Step 3.2-A - バリデーション強化と自動bounds計算

Step 3.2-A.1: ジオメトリバリデーションユーティリティ
- api/lib/validators.py: GeoJSON構造・座標範囲バリデーション

Step 3.2-A.2: bulk import時の自動bounds計算
- api/lib/routers/features.py: インポート後の自動bounds/center更新
- api/lib/models/feature.py: BulkFeatureResponseにbounds情報追加

Step 3.2-A.3: bounds/centerのPydanticバリデーション
- api/lib/models/tileset.py: field_validator追加

Step 3.2-A.4: 既存データ修正スクリプト
- scripts/fix_bounds.py: bounds/center再計算・修正ツール

テストコード:
- api/tests/: 132テスト（conftest.pyに共通フィクスチャ）
- api/tests/README.md: テストドキュメント"

git push origin develop

# Fly.ioデプロイ（必要に応じて）
cd api
fly deploy
```

---

## 8. 参考リソース

### プロジェクトドキュメント

| ファイル | 説明 |
|---------|------|
| `/mnt/project/ROADMAP_S3.md` | Season 3 完全ロードマップ |
| `/mnt/project/HANDOVER_MAIN_REFACTORING.md` | main.pyリファクタリング完了ドキュメント |
| `/mnt/project/geo-base.txt` | 最新ソースコードスナップショット |
| `/mnt/project/MCP_BEST_PRACTICES.md` | MCPサーバー実装ベストプラクティス |
| `api/tests/README.md` | テスト実行ガイド |

### 外部ドキュメント

- [Fly.io Documentation](https://fly.io/docs/)
- [Pydantic V2 Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Documentation](https://docs.pytest.org/)

---

## 9. 次回作業の開始手順

```fish
# 1. リポジトリを最新に更新
cd /path/to/geo-base
git checkout develop
git pull origin develop

# 2. 今回の変更が適用されているか確認
ls -la api/lib/validators.py
ls -la api/tests/
ls -la scripts/fix_bounds.py

# 3. テスト実行確認
cd api
uv run pytest tests/ -v

# 4. 動作確認
curl https://geo-base-api.fly.dev/api/health

# 5. Step 3.2-B の作業を開始
# - mcp/lib/retry.py を参考にAPI側リトライ実装
# - tilesets.py, features.py へのリトライ統合
```

---

## 10. 成果物まとめ

### 今回のセッションで追加・更新されたファイル

| カテゴリ | ファイル | 行数 | 状態 |
|---------|---------|------|------|
| バリデーション | `api/lib/validators.py` | 650 | 新規 |
| モデル | `api/lib/models/__init__.py` | 35 | 更新 |
| モデル | `api/lib/models/feature.py` | 65 | 更新 |
| モデル | `api/lib/models/tileset.py` | 310 | 更新 |
| ルーター | `api/lib/routers/features.py` | 590 | 更新 |
| テスト | `api/tests/__init__.py` | 20 | 新規 |
| テスト | `api/tests/conftest.py` | 280 | 新規 |
| テスト | `api/tests/test_validators.py` | 380 | 新規 |
| テスト | `api/tests/test_tileset_models.py` | 240 | 新規 |
| テスト | `api/tests/test_fix_bounds.py` | 220 | 新規 |
| テスト | `api/tests/README.md` | 180 | 新規 |
| スクリプト | `scripts/fix_bounds.py` | 520 | 新規 |
| 設定 | `api/pyproject.toml` | 75 | 更新 |

**合計**: 約3,500行の新規/更新コード、132テストケース

---

**作成者**: Claude (Anthropic)  
**完了日**: 2025-12-17  
**次回作業**: Phase 2 Step 3.2-B（リトライ機能統合）
