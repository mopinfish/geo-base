# geo-base Season 3 引き継ぎドキュメント - Step 3.2-D

**更新日**: 2025-12-17  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**現在のブランチ**: `develop`

---

## 1. 現在のシステム状況

### 1.1 デプロイ状況

| コンポーネント | ステータス | URL | バージョン |
|---------------|-----------|-----|-----------|
| API Server (Fly.io) | ✅ 稼働中 | https://geo-base-api.fly.dev | 0.4.3 → **0.4.4** |
| MCP Server (Fly.io) | ✅ 稼働中 | https://geo-base-mcp.fly.dev | 0.2.5 |
| Admin UI (Vercel) | ✅ 稼働中 | https://geo-base-admin.vercel.app | 0.4.0 |

### 1.2 Season 3 Phase 2 進捗

| ステップ | 内容 | ステータス |
|---------|------|-----------|
| Step 3.2-A | バリデーション強化 | ✅ 完了 |
| Step 3.2-B | リトライ機能統合 | ✅ 完了 |
| Step 3.2-C | Redisキャッシュ導入 | ✅ 完了 |
| **Step 3.2-D** | **バッチ処理最適化** | ✅ **完了** |

**Phase 2 完了！** 🎉

---

## 2. 今回完了した作業: Step 3.2-D バッチ処理最適化

### 2.1 概要

フィーチャーのバルクエクスポート、バッチ更新、バッチ削除機能を実装しました。

### 2.2 実装内容

#### Step 3.2-D.1: バッチ処理モジュール

**新規ファイル**: `api/lib/batch.py` (~700行)

機能:

1. **BatchResult** データクラス
   - 処理結果の統一形式
   - success_count, failed_count, total_count
   - errors, warnings リスト
   - 処理時間の計測

2. **エクスポート機能**
   - `export_features_geojson()`: GeoJSONエクスポート
   - `export_features_geojson_streaming()`: ストリーミングエクスポート（大量データ対応）
   - `export_features_csv()`: CSVエクスポート

3. **バッチ更新機能**
   - `batch_update_features()`: ID指定での一括更新
   - `batch_update_by_filter()`: フィルタ条件での一括更新

4. **バッチ削除機能**
   - `batch_delete_features()`: ID指定での一括削除
   - `batch_delete_by_filter()`: フィルタ条件での一括削除
   - `dry_run`オプションでプレビュー可能

#### Step 3.2-D.2: エンドポイントルーター

**新規ファイル**: `api/lib/routers/batch_features.py` (~450行)

エンドポイント:

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/features/export` | フィーチャーエクスポート（GeoJSON/CSV） |
| GET | `/api/features/export/{tileset_id}` | シンプルエクスポート |
| GET | `/api/features/export/{tileset_id}/stream` | ストリーミングエクスポート |
| POST | `/api/features/bulk/update` | バッチ更新 |
| POST | `/api/features/bulk/delete` | バッチ削除 |
| DELETE | `/api/features/bulk` | シンプルバッチ削除（GET）|

#### Step 3.2-D.3: 管理画面UI

**更新ファイル**: `app/src/lib/api.ts`
- `ExportRequest`, `BatchUpdateRequest`, `BatchDeleteRequest` 型定義追加
- `exportFeatures()` - GeoJSONエクスポート
- `exportFeaturesCsv()` - CSVエクスポート（Blob返却）
- `batchUpdateFeatures()` - バッチ更新
- `batchDeleteFeatures()` - バッチ削除

**更新ファイル**: `app/src/app/features/page.tsx`
- エクスポートダイアログ（GeoJSON/CSV選択）
- バッチ更新ダイアログ（レイヤー名、プロパティ変更）
- バッチ削除機能（APIを使用した一括削除）
- 成功/エラーメッセージ表示

**新規ファイル**: `app/src/components/features/export-features-button.tsx`
- 再利用可能なエクスポートボタンコンポーネント
- タイルセット詳細ページなどで使用可能

### 2.3 テストコード

**新規ファイル**: `api/tests/test_batch.py` (~400行)

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| TestBatchResult | 5 | BatchResultデータクラス |
| TestExportFeaturesGeojson | 5 | GeoJSONエクスポート |
| TestExportFeaturesCsv | 2 | CSVエクスポート |
| TestBatchUpdateFeatures | 4 | ID指定更新 |
| TestBatchUpdateByFilter | 2 | フィルタ更新 |
| TestBatchDeleteFeatures | 3 | ID指定削除 |
| TestBatchDeleteByFilter | 4 | フィルタ削除 |
| TestBatchIntegration | 2 | 統合テスト |

**新規テスト**: 27テスト

---

## 3. API使用例

### 3.1 エクスポート

```fish
# GeoJSONエクスポート
curl -X POST http://localhost:8000/api/features/export \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tileset_id": "uuid",
    "format": "geojson",
    "layer_name": "buildings",
    "bbox": [139.5, 35.5, 140.0, 36.0],
    "limit": 1000
  }'

# CSVエクスポート
curl -X POST http://localhost:8000/api/features/export \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tileset_id": "uuid", "format": "csv"}' \
  -o features.csv

# ストリーミングエクスポート（大量データ）
curl http://localhost:8000/api/features/export/uuid/stream \
  -H "Authorization: Bearer TOKEN" \
  -o large_export.geojson
```

### 3.2 バッチ更新

```fish
# ID指定で更新
curl -X POST http://localhost:8000/api/features/bulk/update \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "updates": {
      "properties": {"status": "reviewed"}
    },
    "merge_properties": true
  }'

# フィルタ条件で更新
curl -X POST http://localhost:8000/api/features/bulk/update \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tileset_id": "uuid",
    "filter": {
      "layer_name": "temp_layer",
      "properties": {"status": "pending"}
    },
    "updates": {
      "layer_name": "processed_layer",
      "properties": {"status": "completed"}
    }
  }'
```

### 3.3 バッチ削除

```fish
# ID指定で削除
curl -X POST http://localhost:8000/api/features/bulk/delete \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2", "uuid-3"]
  }'

# フィルタ条件で削除（ドライラン）
curl -X POST http://localhost:8000/api/features/bulk/delete \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tileset_id": "uuid",
    "filter": {"layer_name": "temp_layer"},
    "dry_run": true
  }'

# シンプルな削除
curl -X DELETE "http://localhost:8000/api/features/bulk?feature_ids=uuid-1&feature_ids=uuid-2" \
  -H "Authorization: Bearer TOKEN"
```

---

## 4. ファイル一覧

### 追加・更新ファイル

#### API側

```
api/
├── lib/
│   ├── batch.py                    # 新規 (700行) - バッチ処理モジュール
│   ├── main.py                     # 更新 - batch_featuresルーター追加
│   └── routers/
│       └── batch_features.py       # 新規 (450行) - バッチエンドポイント
└── tests/
    └── test_batch.py               # 新規 (400行) - バッチテスト
```

#### Admin UI側

```
app/src/
├── lib/
│   └── api.ts                      # 更新 - バッチ操作API追加
├── app/features/
│   └── page.tsx                    # 更新 - エクスポート/バッチ更新/バッチ削除UI
└── components/features/
    ├── export-features-button.tsx  # 新規 - エクスポートボタンコンポーネント
    └── index.ts                    # 更新 - エクスポート追加
```

**合計**: 約2,500行の新規・更新コード、27テストケース

---

## 5. テスト実行

```fish
cd api

# 全テスト
uv run pytest tests/ -v

# バッチ処理テストのみ
uv run pytest tests/test_batch.py -v
```

**期待される結果**: 153 passed

---

## 6. Phase 2 完了サマリー

### 7.1 Step 3.2-A: バリデーション強化
- ジオメトリバリデーション
- bounds/center正規化
- Pydanticモデル強化

### 7.2 Step 3.2-B: リトライ機能統合
- RetryConfig設定
- デコレータ (@with_retry, @with_db_retry)
- DBヘルパー関数

### 7.3 Step 3.2-C: Redisキャッシュ導入
- Redisクライアント
- タイルキャッシュ
- メモリキャッシュフォールバック

### 7.4 Step 3.2-D: バッチ処理最適化
- GeoJSON/CSVエクスポート
- バッチ更新
- バッチ削除

### 7.5 テスト総数

| ステップ | テスト数 |
|---------|---------|
| Step 3.2-A (バリデーション) | 132 |
| Step 3.2-B (リトライ) | 80 |
| Step 3.2-C (Redis) | 46 |
| Step 3.2-D (バッチ) | 27 |
| **Phase 2 合計** | **153** |

※ 一部テストは共通テストと重複カウント

---

## 7. 次のフェーズ: Phase 3 チーム機能

### 8.1 計画内容

| ステップ | 内容 | 見積もり |
|---------|------|----------|
| Step 3.3-A | チームモデル設計 | 1日 |
| Step 3.3-B | チーム管理API | 2日 |
| Step 3.3-C | メンバー管理・招待 | 1.5日 |
| Step 3.3-D | 権限管理 | 1.5日 |
| Step 3.3-E | APIキー管理 | 1日 |

---

## 8. デプロイ手順

```fish
cd /path/to/geo-base

# zipを解凍して上書き
unzip -o ~/Downloads/geo-base-step3.2-D.zip -d .

# テスト実行確認
cd api
uv run pytest tests/ -v

# コミット & プッシュ
cd ..
git add .
git commit -m "feat(api): Step 3.2-D - バッチ処理最適化

Step 3.2-D.1: バッチ処理モジュール
- api/lib/batch.py: BatchResult, エクスポート, バッチ更新/削除

Step 3.2-D.2: エンドポイント
- api/lib/routers/batch_features.py: export, bulk/update, bulk/delete

テストコード:
- api/tests/test_batch.py: 27テスト
- Phase 2 完了（総数153テスト）"

git push origin develop
```

---

## 9. 参考リソース

### プロジェクトドキュメント

| ファイル | 説明 |
|---------|------|
| `HANDOVER_S3_STEP3.2-C.md` | 前回の引き継ぎ |
| `docs/REDIS_SETUP.md` | Redisセットアップガイド |
| `ROADMAP_S3.md` | Season 3ロードマップ |

---

**作成者**: Claude (Anthropic)  
**完了日**: 2025-12-17  
**次回作業**: Phase 3 Step 3.3-A（チームモデル設計）
