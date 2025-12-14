# geo-base セカンドシーズン 引き継ぎドキュメント

## MCPサーバー機能拡充プロジェクト

**最終更新**: 2025-12-14  
**プロジェクト**: geo-base MCP Server Enhancement  
**フェーズ**: セカンドシーズン Phase 1進行中

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
| 現行MCPバージョン | 0.2.0 |
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

### 2.3 現在のファイル構成（Step 2.5-A完了後）

```
mcp/
├── server.py              # FastMCPサーバー本体
├── config.py              # 設定管理（LOG_LEVEL追加）
├── logger.py              # 🆕 ロギング基盤
├── tools/
│   ├── __init__.py        # 更新: エクスポート整理
│   ├── tilesets.py        # 更新: ロギング追加
│   ├── features.py        # 更新: ロギング追加
│   ├── geocoding.py       # 更新: ロギング追加
│   └── crud.py            # 更新: ロギング追加
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_logger.py     # 🆕 ロギングテスト
│   ├── test_tools.py
│   ├── test_geocoding.py
│   ├── test_crud.py
│   └── live_test.py
├── Dockerfile
├── fly.toml
├── pyproject.toml         # 更新: version 0.2.0, logger.py追加
└── uv.lock
```

---

## 3. 開発フェーズ進捗

### Phase 1: 基盤強化

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-A | ロギング基盤の追加 | ✅ 完了 | Claude | logger.py作成、全ツールにロギング追加 |
| 2.5-B | エラーハンドリング・リトライ | 🔲 未着手 | - | errors.py, retry.py作成 |

### Phase 2: 機能拡充

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-C | 統計ツールの追加 | 🔲 未着手 | - | tools/stats.py作成 |
| 2.5-D | 空間分析ツールの追加 | 🔲 未着手 | - | **最重要ゴール** tools/analysis.py作成 |

### Phase 3: 品質向上

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-E | 入力バリデーション強化 | 🔲 未着手 | - | validators.py作成 |
| 2.5-F | テストコードの拡充 | 🔲 未着手 | - | カバレッジ80%目標 |

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

## 5. 次のアクション

### 5.1 即座に着手可能なタスク

1. **Step 2.5-B: エラーハンドリング強化**
   - [ ] `mcp/errors.py` を作成（カスタム例外）
   - [ ] `mcp/retry.py` を作成（tenacity導入）
   - [ ] pyproject.toml に tenacity を追加
   - [ ] 各ツールにリトライ処理を追加

### 5.2 依存関係の追加予定

```toml
# pyproject.toml に追加予定
dependencies = [
    # 既存
    "fastmcp>=2.0.0",
    "httpx>=0.26.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    # 新規追加
    "tenacity>=8.0.0",
]
```

---

## 6. 既知の問題・注意点

### 6.1 制限事項

| 項目 | 詳細 |
|------|------|
| Vercel環境 | rasterioが使用不可（GDAL依存） |
| PMTiles | 読み取りのみ対応（書き込み未対応） |
| 認証 | API_TOKENが必須のCRUD操作あり |

### 6.2 環境変数

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

## 7. 参考資料

### 7.1 サンプルコード（プロジェクト添付）

| ファイル | 内容 |
|---------|------|
| quickstart-resources.txt | Anthropic公式クイックスタート |
| openweather-mcp.txt | 天気予報MCPサーバー |
| chillax-mcp-server.txt | 過ごし方提案MCPサーバー |
| documentor.txt | 社内ドキュメント検索MCPサーバー |

### 7.2 外部ドキュメント

- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [tenacity Documentation](https://tenacity.readthedocs.io/)

---

## 8. 連絡先・質問

作業を再開する際は、このドキュメントと [MCP_ROADMAP_S2.md](./MCP_ROADMAP_S2.md) を参照してください。

---

## 更新履歴

| 日付 | 内容 | 担当 |
|------|------|------|
| 2025-12-14 | 初版作成（セカンドシーズン準備） | Claude |
| 2025-12-14 | Step 2.5-A完了（ロギング基盤追加） | Claude |
