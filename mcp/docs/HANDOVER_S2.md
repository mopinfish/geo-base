# geo-base セカンドシーズン 引き継ぎドキュメント

## MCPサーバー機能拡充プロジェクト

**最終更新**: 2025-12-14  
**プロジェクト**: geo-base MCP Server Enhancement  
**フェーズ**: セカンドシーズン準備完了

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

### 2.3 現在のファイル構成

```
mcp/
├── server.py              # FastMCPサーバー本体
├── config.py              # 設定管理
├── tools/
│   ├── __init__.py
│   ├── tilesets.py        # タイルセット関連
│   ├── features.py        # フィーチャー関連
│   ├── geocoding.py       # ジオコーディング
│   └── crud.py            # CRUD操作
├── tests/
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_geocoding.py
│   ├── test_crud.py
│   └── live_test.py
├── Dockerfile
├── fly.toml
├── pyproject.toml
└── uv.lock
```

---

## 3. 開発フェーズ進捗

### Phase 1: 基盤強化

| Step | 内容 | ステータス | 担当 | 備考 |
|------|------|-----------|------|------|
| 2.5-A | ロギング基盤の追加 | 🔲 未着手 | - | logger.py作成 |
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

## 4. 次のアクション

### 4.1 即座に着手可能なタスク

1. **Step 2.5-A: ロギング基盤の追加**
   - [ ] `mcp/logger.py` を作成
   - [ ] 各ツールにロギングを追加
   - [ ] 環境変数 `LOG_LEVEL` 対応

2. **Step 2.5-B: エラーハンドリング強化**
   - [ ] `mcp/errors.py` を作成（カスタム例外）
   - [ ] `mcp/retry.py` を作成（tenacity導入）
   - [ ] pyproject.toml に tenacity を追加

### 4.2 依存関係の追加予定

```toml
# pyproject.toml に追加
dependencies = [
    # 既存
    "fastmcp>=0.1.0",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0",
    # 新規追加
    "tenacity>=8.0.0",
]
```

---

## 5. 技術的なメモ

### 5.1 ロギング実装パターン

```python
# mcp/logger.py
import logging
import os

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

### 5.2 リトライ実装パターン

```python
# mcp/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)
async def fetch_with_retry(url: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

### 5.3 tool_analyze_area 設計案

```python
@mcp.tool()
async def tool_analyze_area(
    bbox: str,
    tileset_id: str | None = None,
    analysis_type: str = "summary",
) -> dict:
    """
    指定範囲内の地理空間データを分析
    
    Args:
        bbox: バウンディングボックス "minx,miny,maxx,maxy" (WGS84)
        tileset_id: 分析対象タイルセットID
        analysis_type: "summary" | "density" | "distribution" | "full"
    
    Returns:
        {
            "bbox": {...},
            "area_km2": 12.5,
            "feature_count": 150,
            "geometry_distribution": {
                "Point": 100,
                "LineString": 30,
                "Polygon": 20
            },
            "density": {
                "features_per_km2": 12.0
            },
            "layers": ["default", "buildings", "roads"]
        }
    """
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
