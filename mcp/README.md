# geo-base MCP Server

MCP (Model Context Protocol) Server for geo-base.

## 機能

- タイルセットメタデータ取得
- タイル取得
- フィーチャー検索
- 空間分析

## セットアップ

```bash
# 依存関係インストール
uv sync

# サーバー起動
uv run python server.py
```

## 環境変数

`.env.example`を参照してください。
