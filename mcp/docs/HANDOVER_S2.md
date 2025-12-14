# geo-base セカンドシーズン 引き継ぎドキュメント

## MCPサーバー機能拡充プロジェクト

**最終更新**: 2025-12-14  
**プロジェクト**: geo-base MCP Server Enhancement  
**フェーズ**: セカンドシーズン Phase 2完了（最重要ゴール達成）

---

## 1. プロジェクト概要

### 1.1 目的

geo-base MCPサーバーの機能を拡充し、以下を実現する：

- **最重要ゴール**: `tool_analyze_area`（空間分析ツール）の実装
- 保守運用性の向上（ロギング、エラーハンドリング）
- 新規ツールの追加による機能拡充
- テストカバレッジの向上

### 1.2 関連ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [MCP_ROADMAP_S2.md](./MCP_ROADMAP_S2.md) | セカンドシーズンのロードマップ |
| [MCP_BEST_PRACTICES.md](./MCP_BEST_PRACTICES.md) | MCPサーバー開発のベストプラクティス |
| [MCP_PRESENTATION.md](./MCP_PRESENTATION.md) | プレゼン用シナリオ |
| [HANDOVER.md](./HANDOVER.md) | ファーストシーズンの引き継ぎ |

### 1.3 リポジトリ情報

| 項目 | 値 |
|------|-----|
| リポジトリ | https://github.com/mopinfish/geo-base |
| 対象ディレクトリ | `/mcp` |
| 現行MCPバージョン | 0.2.4 |
| 目標バージョン | 1.0.0 |
| APIバージョン | 0.4.0 |

---

## 2. 現在の状況

### 2.1 システム状況

| コンポーネント | ステータス | URL |
|---------------|-----------|-----|
| API Server | ✅ 稼働中 | https://geo-base-puce.vercel.app |
| MCP Server | ✅ 稼働中 | https://geo-base-mcp.fly.dev |
| Admin UI | ✅ 稼働中 | https://geo-base-admin.vercel.app |

### 2.2 実装済みツール（16個）

```
タイルセット関連（3ツール）
├── tool_list_tilesets      - タイルセット一覧取得
├── tool_get_tileset        - タイルセット詳細取得
└── tool_get_tileset_tilejson - TileJSON取得

フィーチャー関連（2ツール）
├── tool_search_features    - フィーチャー検索
└── tool_get_feature        - フィーチャー詳細取得

タイル関連（1ツール）
└── tool_get_tile_url       - タイルURL生成

ユーティリティ（2ツール）
├── tool_health_check       - ヘルスチェック
└── tool_get_server_info    - サーバー情報取得

ジオコーディング（2ツール）
├── tool_geocode            - 住所→座標変換
└── tool_reverse_geocode    - 座標→住所変換

CRUD操作（6ツール）
├── tool_create_tileset     - タイルセット作成
├── tool_update_tileset     - タイルセット更新
├── tool_delete_tileset     - タイルセット削除
├── tool_create_feature     - フィーチャー作成
├── tool_update_feature     - フィーチャー更新
└── tool_delete_feature     - フィーチャー削除
```

### 2.3 現在のファイル構成（Step 2.5-B完了後）

```
mcp/
├── server.py              # FastMCPサーバー本体
├── config.py              # 設定管理（LOG_LEVEL追加）
├── logger.py              # ロギング基盤
├── errors.py              # 🆕 カスタム例外・エラーハンドリング
├── retry.py               # 🆕 リトライ機能（tenacity）
├── tools/
│   ├── __init__.py        # エクスポート整理
│   ├── tilesets.py        # ロギング追加済み
│   ├── features.py        # ロギング追加済み
│   ├── geocoding.py       # ロギング追加済み
│   └── crud.py            # ロギング追加済み
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_logger.py     # ロギングテスト
│   ├── test_errors.py     # 🆕 エラーハンドリングテスト
│   ├── test_retry.py      # 🆕 リトライテスト
│   ├── test_tools.py
│   ├── test_geocoding.py
│   ├── test_crud.py
│   └── live_test.py
├── docs/
│   ├── HANDOVER_S2.md     # 引き継ぎドキュメント
│   └── MCP_BEST_PRACTICES.md
├── Dockerfile
├── fly.toml
├── pyproject.toml         # 更新: version 0.2.1, tenacity追加
└── uv.lock
```

---

## 3. 開発フェーズ進捗

### Phase 1: 基盤強化

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-A | ロギング基盤の追加 | ✅ 完了 | Claude | logger.py作成、全ツールにロギング追加 |
| 2.5-B | エラーハンドリング・リトライ | ✅ 完了 | Claude | errors.py, retry.py作成、tenacity導入 |

### Phase 2: 機能拡充

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-C | 統計ツールの追加 | ✅ 完了 | Claude | tools/stats.py作成、4ツール追加 |
| 2.5-D | 空間分析ツールの追加 | ✅ 完了 | Claude | **最重要ゴール** tools/analysis.py作成、4ツール追加 |

### Phase 3: 品質向上

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-E | 入力バリデーション強化 | ✅ 完了 | Claude | validators.py作成、20+関数 |
| 2.5-F | テストコードの拡充 | ✅ 完了 | Claude | カバレッジ85%達成 |

**凡例**: ✅ 完了 | 🔄 進行中 | 🔲 未着手 | ⏸️ 保留

---

## 4. Step 2.5-A 完了内容

### 4.1 追加・更新ファイル

| ファイル | 内容 |
|---------|------|
| `mcp/logger.py` | ロギング基盤モジュール |
| `mcp/config.py` | `LOG_LEVEL`設定追加、バージョン0.2.0 |
| `mcp/server.py` | 起動時ログ追加 |
| `mcp/tools/tilesets.py` | ToolCallLogger追加 |
| `mcp/tools/features.py` | ToolCallLogger追加 |
| `mcp/tools/geocoding.py` | ToolCallLogger追加 |
| `mcp/tools/crud.py` | ToolCallLogger追加 |
| `mcp/tools/__init__.py` | エクスポート整理 |
| `mcp/tests/test_logger.py` | ロギングテスト |

### 4.2 logger.py の機能

```python
# 主要コンポーネント
- MCPFormatter: カスタムログフォーマッター（extra fieldsサポート）
- ToolCallLogger: ツール呼び出しのコンテキストマネージャー
- get_logger(): 名前付きロガーの取得（キャッシュ付き）
- get_log_level(): 環境変数からログレベルを取得

# 使用例
from logger import get_logger, ToolCallLogger

logger = get_logger(__name__)

async def my_tool(param: str) -> dict:
    with ToolCallLogger(logger, "my_tool", param=param) as log:
        result = await process(param)
        log.set_result(result)
        return result
```

### 4.3 環境変数

```bash
# 追加された環境変数
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 5. Step 2.5-B 完了内容

### 5.1 追加・更新ファイル

| ファイル | 内容 |
|---------|------|
| `mcp/errors.py` | カスタム例外クラス、エラーハンドリング関数 |
| `mcp/retry.py` | tenacityベースのリトライ機能 |
| `mcp/config.py` | バージョン0.2.1に更新 |
| `mcp/pyproject.toml` | tenacity依存関係追加、バージョン0.2.1 |
| `mcp/tests/test_errors.py` | エラーハンドリングテスト（19テスト） |
| `mcp/tests/test_retry.py` | リトライ機能テスト |

### 5.2 errors.py の機能

```python
# カスタム例外クラス
- MCPError: 基底例外クラス
- ValidationError: 入力バリデーションエラー
- APIError: 外部API呼び出しエラー
- AuthenticationError: 認証エラー
- NotFoundError: リソース未発見エラー
- NetworkError: ネットワークエラー

# エラーコード（ErrorCode Enum）
- VALIDATION_ERROR, AUTH_REQUIRED, FORBIDDEN, NOT_FOUND
- NETWORK_ERROR, TIMEOUT, SERVER_ERROR, UNKNOWN_ERROR

# ユーティリティ関数
- handle_api_error(e, context): 例外を標準化レスポンスに変換
- create_error_response(message, code, **kwargs): エラーレスポンス作成

# 使用例
from errors import handle_api_error, ValidationError, ErrorCode

try:
    response = await client.get(url)
    response.raise_for_status()
except Exception as e:
    return handle_api_error(e, {"url": url})
```

### 5.3 retry.py の機能

```python
# リトライ付きHTTP関数
- fetch_with_retry(url, params, headers, timeout, max_attempts)
- post_with_retry(url, json, headers, timeout, max_attempts)
- put_with_retry(url, json, headers, timeout, max_attempts)
- delete_with_retry(url, headers, timeout, max_attempts)

# RetryableClient: コンテキストマネージャー付きクライアント
async with RetryableClient(headers=auth_headers) as client:
    data = await client.get("https://api.example.com/data")
    result = await client.post("https://api.example.com/create", json={...})

# リトライ設定（環境変数で設定可能）
- RETRY_MAX_ATTEMPTS=3    # 最大リトライ回数
- RETRY_MIN_WAIT=1        # 最小待機時間（秒）
- RETRY_MAX_WAIT=10       # 最大待機時間（秒）

# リトライ対象例外
- httpx.TimeoutException
- httpx.NetworkError
- httpx.ConnectError
```

### 5.4 環境変数

```bash
# 追加された環境変数
RETRY_MAX_ATTEMPTS=3      # リトライ最大回数
RETRY_MIN_WAIT=1          # 最小待機時間（秒）
RETRY_MAX_WAIT=10         # 最大待機時間（秒）
```

---

## 6. Step 2.5-C 完了内容

### 6.1 追加ファイル

| ファイル | 内容 |
|---------|------|
| `mcp/tools/stats.py` | 統計ツールモジュール（4関数） |
| `mcp/tests/test_stats.py` | 統計ツールテスト |

### 6.2 stats.py の機能

```python
# 統計ツール関数
- get_tileset_stats(tileset_id): タイルセットの包括的統計
  - フィーチャー数、ジオメトリタイプ分布、レイヤー別統計、座標点数

- get_feature_distribution(tileset_id?, bbox?): ジオメトリタイプ分布
  - タイプ別カウント、パーセンテージ計算

- get_layer_stats(tileset_id): レイヤー別統計
  - レイヤー毎のフィーチャー数、プロパティキー一覧

- get_area_stats(bbox, tileset_id?): エリア統計
  - 面積計算(km²)、密度計算、レイヤー分布
```

---

## 7. Step 2.5-D 完了内容 (最重要ゴール)

### 7.1 追加ファイル

| ファイル | 内容 |
|---------|------|
| `mcp/tools/analysis.py` | 空間分析ツールモジュール（4関数） |
| `mcp/tests/test_analysis.py` | 空間分析ツールテスト |

### 7.2 analysis.py の機能

```python
# 空間分析ツール関数
- analyze_area(bbox, tileset_id?, include_density?, include_clustering?):
  - 包括的な空間分析: 密度グリッド、ホットスポット検出、クラスタリング

- calculate_distance(lat1, lng1, lat2, lng2):
  - Haversine距離計算、方位計算

- find_nearest_features(lat, lng, radius_km, limit, tileset_id?, layer?):
  - 近傍フィーチャー検索、距離順ソート

- get_buffer_zone_features(lat, lng, inner_radius_km, outer_radius_km, tileset_id?):
  - リングバッファ（ドーナツ型）内のフィーチャー検索、密度計算
```

### 7.3 ヘルパー関数

```python
# 空間計算ヘルパー
- _haversine_distance(): 大圏距離計算（km）
- _get_feature_centroid(): フィーチャーの重心座標取得
- _expand_bbox(): バウンディングボックスのバッファ拡張
- _bearing_to_direction(): 方位角をコンパス方向に変換
```

---

## 8. 現在のツール一覧（20ツール）

### 8.1 タイルセット関連 (3)
- `tool_list_tilesets` - タイルセット一覧
- `tool_get_tileset` - タイルセット詳細
- `tool_get_tileset_tilejson` - TileJSON取得

### 8.2 フィーチャー関連 (2)
- `tool_search_features` - フィーチャー検索
- `tool_get_feature` - フィーチャー詳細

### 8.3 ジオコーディング (2)
- `tool_geocode` - 住所→座標
- `tool_reverse_geocode` - 座標→住所

### 8.4 CRUD操作 (6)
- `tool_create_tileset` / `tool_update_tileset` / `tool_delete_tileset`
- `tool_create_feature` / `tool_update_feature` / `tool_delete_feature`

### 8.5 ユーティリティ (3)
- `tool_get_tile_url` - タイルURL生成
- `tool_health_check` - ヘルスチェック
- `tool_get_server_info` - サーバー情報

### 8.6 統計ツール (4) - NEW
- `tool_get_tileset_stats` - タイルセット統計
- `tool_get_feature_distribution` - ジオメトリ分布
- `tool_get_layer_stats` - レイヤー別統計
- `tool_get_area_stats` - エリア統計

### 8.7 空間分析ツール (4) - NEW
- `tool_analyze_area` - 包括的空間分析
- `tool_calculate_distance` - 距離計算
- `tool_find_nearest_features` - 近傍検索
- `tool_get_buffer_zone_features` - バッファゾーン分析

---

## 9. Step 2.5-E 完了内容

### 9.1 追加ファイル

| ファイル | 内容 |
|---------|------|
| `mcp/validators.py` | 入力バリデーションモジュール（20+関数） |
| `mcp/tests/test_validators.py` | バリデーションテスト（50+テスト） |

### 9.2 validators.py の機能

```python
# ValidationResult データクラス
@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None
    code: str | None = None
    value: Any = None  # パース済み値

# UUID検証
- validate_uuid(value, field_name) -> ValidationResult
- is_valid_uuid(value) -> bool

# 座標検証
- validate_latitude(value, field_name) -> ValidationResult
- validate_longitude(value, field_name) -> ValidationResult
- validate_coordinates(lat, lng) -> ValidationResult

# バウンディングボックス検証
- validate_bbox(bbox, field_name) -> ValidationResult  # 文字列・リスト対応
- parse_bbox(bbox_str) -> tuple | None  # 後方互換性用

# ズームレベル・タイル座標検証
- validate_zoom(value, min_zoom, max_zoom, field_name) -> ValidationResult
- validate_tile_coordinates(z, x, y) -> ValidationResult

# タイルセット設定検証
- validate_tileset_type(value) -> ValidationResult  # vector, raster, pmtiles
- validate_tile_format(value) -> ValidationResult   # pbf, png, jpg, webp, geojson

# GeoJSONジオメトリ検証
- validate_geometry(geometry, field_name) -> ValidationResult
  - Point, LineString, Polygon, Multi*, GeometryCollection対応
  - 座標構造の検証

# 文字列・数値検証
- validate_non_empty_string(value, field_name, max_length, pattern)
- validate_positive_number(value, field_name, allow_zero)
- validate_range(value, field_name, min_value, max_value)
- validate_limit(value, field_name, min_value, max_value)

# フィルター検証
- validate_filter(filter_str) -> ValidationResult  # "key=value"形式
```

### 9.3 使用例

```python
from validators import validate_uuid, validate_bbox, validate_geometry

# UUID検証
result = validate_uuid(tileset_id, "tileset_id")
if not result.valid:
    return result.to_error_response()

# bbox検証（文字列またはリスト）
result = validate_bbox("139.5,35.5,140.0,36.0")
if result.valid:
    min_lng, min_lat, max_lng, max_lat = result.value

# ジオメトリ検証
result = validate_geometry({"type": "Point", "coordinates": [139.7, 35.6]})
if not result.valid:
    return {"error": result.error, "code": result.code}
```

---

## 10. Step 2.5-F 完了内容

### 10.1 追加テストファイル

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `tests/test_crud.py` | 16 | CRUD操作（タイルセット・フィーチャー）テスト |
| `tests/test_geocoding.py` | 14 | ジオコーディング・逆ジオコーディングテスト |
| `tests/test_tools.py` | 20 | タイルセット・フィーチャー検索ツールテスト |
| `tests/test_integration.py` | 16 | 統合テスト（バリデータ+ツール連携） |

### 10.2 テストカバレッジ

```
Name                        Stmts   Miss  Cover
---------------------------------------------------------
config.py                      17      0   100%
errors.py                     121      7    94%
logger.py                      89     15    83%
retry.py                      115     27    77%
validators.py                 219     41    81%
tools/__init__.py               7      0   100%
tools/analysis.py             298     58    81%
tools/crud.py                 287    120    58%
tools/features.py             143     27    81%
tools/geocoding.py             95     19    80%
tools/stats.py                239     49    79%
tools/tilesets.py             111     31    72%
---------------------------------------------------------
TOTAL                        4023    598    85%
```

### 10.3 テスト実行結果

- **総テスト数**: 253
- **パス**: 250
- **スキップ**: 3（複雑なasyncモック設定が必要なテスト）
- **カバレッジ**: 85%（目標80%達成）

### 10.4 その他の修正

- `tools/crud.py`: ログのextraフィールド名を`name`から`tileset_name`に変更（LogRecord予約フィールド衝突回避）

---

## 11. 次のアクション

### 11.1 Phase 3完了

Phase 3（品質向上）は全ステップ完了しました。

### 11.2 オプショナル改善

1. **既存ツールへのバリデーション統合**
   - [ ] tools/crud.py にvalidators適用
   - [ ] tools/analysis.py にvalidators適用
   - [ ] tools/stats.py にvalidators適用

2. **既存ツールへのリトライ機能統合**
   - [ ] tilesets.py を retry.py の関数で更新
   - [ ] features.py を retry.py の関数で更新

3. **パフォーマンス改善**
   - [ ] キャッシュ機能の追加
   - [ ] バッチ処理の実装

4. **スキップされたテストの修正**
   - [ ] 複雑なasyncモック設定のリファクタリング

---

## 10. 既知の問題・注意点

### 10.1 制限事項

| 項目 | 詳細 |
|------|------|
| Vercel環境 | rasterioが使用不可（GDAL依存） |
| PMTiles | 読み取りのみ対応（書き込み未対応） |
| 認証 | API_TOKENが必須のCRUD操作あり |

### 10.2 環境変数

```bash
# 必須
TILE_SERVER_URL=https://geo-base-puce.vercel.app

# オプション
API_TOKEN=xxxxx           # CRUD操作に必要
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
MCP_TRANSPORT=stdio       # stdio, sse, streamable-http
MCP_HOST=0.0.0.0          # SSE/HTTP時のホスト
MCP_PORT=8080             # SSE/HTTP時のポート
```

---

## 11. 参考資料

### 11.1 サンプルコード（プロジェクト添付）

| ファイル | 内容 |
|---------|------|
| quickstart-resources.txt | Anthropic公式クイックスタート |
| openweather-mcp.txt | 天気予報MCPサーバー |
| chillax-mcp-server.txt | 過ごし方提案MCPサーバー |
| documentor.txt | 社内ドキュメント検索MCPサーバー |

### 11.2 外部ドキュメント

- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [tenacity Documentation](https://tenacity.readthedocs.io/)

---

## 12. 連絡先・質問

作業を再開する際は、このドキュメントと [MCP_ROADMAP_S2.md](./MCP_ROADMAP_S2.md) を参照してください。

---

## 更新履歴

| 日付 | 内容 | 担当 |
|------|------|------|
| 2025-12-14 | 初版作成（セカンドシーズン準備） | Claude |
| 2025-12-14 | Step 2.5-A完了（ロギング基盤追加） | Claude |
| 2025-12-14 | Step 2.5-B完了（エラーハンドリング・リトライ追加） | Claude |
| 2025-12-14 | Step 2.5-C完了（統計ツール4種追加）バージョン0.2.2 | Claude |
| 2025-12-14 | Step 2.5-D完了（空間分析ツール4種追加）バージョン0.2.2 | Claude |
| 2025-12-14 | Step 2.5-E完了（入力バリデーション強化）バージョン0.2.3 | Claude |
| 2025-12-14 | Step 2.5-F完了（テストコード拡充、カバレッジ85%）バージョン0.2.4 | Claude |
