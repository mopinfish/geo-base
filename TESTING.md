# geo-base 動作確認手順

このドキュメントでは、geo-baseプロジェクトのローカル環境およびリモート本番環境での動作確認手順を説明します。

---

## 📁 プロジェクト構成

```
geo-base/
├── api/                    # FastAPI タイルサーバー (Vercel)
│   └── lib/main.py         # メインアプリケーション
├── mcp/                    # MCP サーバー (Fly.io)
│   ├── server.py           # MCPサーバー本体
│   ├── tools/              # MCPツール
│   │   ├── tilesets.py     # タイルセット操作
│   │   ├── features.py     # フィーチャー操作
│   │   ├── geocoding.py    # ジオコーディング
│   │   └── crud.py         # CRUD操作
│   └── tests/              # テストファイル
│       ├── test_tools.py
│       ├── test_geocoding.py
│       ├── test_crud.py
│       └── live_test.py    # ライブテスト
└── ...
```

---

## 1. ユニットテストの実行

### 1.1 MCPサーバーのテスト

```fish
# MCPディレクトリに移動
cd /path/to/geo-base/mcp

# 開発依存関係をインストール
uv sync --extra dev

# 全テストを実行
uv run pytest -v

# 特定のテストファイルを実行
uv run pytest tests/test_tools.py -v      # タイルセット・フィーチャーツール
uv run pytest tests/test_geocoding.py -v  # ジオコーディングツール
uv run pytest tests/test_crud.py -v       # CRUDツール

# カバレッジ付きでテスト実行（オプション）
uv run pytest --cov=tools --cov-report=html -v
```

**期待される出力:**
```
============================= test session starts ==============================
...
tests/test_crud.py::TestCreateTileset::test_create_tileset_success PASSED
tests/test_crud.py::TestCreateTileset::test_create_tileset_auth_required PASSED
...
============================== 13 passed in 0.75s ==============================
```

---

## 2. ローカル環境での動作確認

### 2.1 前提条件

- Python 3.11+
- uv (Pythonパッケージマネージャー)
- Node.js 18+（APIサーバー用）
- Docker（オプション、ローカルDB用）
- PostgreSQL + PostGIS（タイルサーバー用）

### 2.2 環境変数の設定

#### APIサーバー（api/.env）
```env
DATABASE_URL=postgresql://user:password@localhost:5432/geo_base
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

#### MCPサーバー（mcp/.env）
```env
TILE_SERVER_URL=http://localhost:3000
API_TOKEN=your-jwt-token  # CRUD操作用（オプション）
MCP_TRANSPORT=stdio
DEBUG=true
```

### 2.3 APIサーバーの起動

```fish
# APIディレクトリに移動
cd /path/to/geo-base/api

# 依存関係をインストール
uv sync

# 開発サーバーを起動
uv run uvicorn lib.main:app --reload --port 3000

# または Vercel CLI を使用
vercel dev
```

**動作確認:**
```fish
# ヘルスチェック
curl http://localhost:3000/api/health

# タイルセット一覧
curl http://localhost:3000/api/tilesets

# フィーチャー検索
curl "http://localhost:3000/api/features?bbox=139.5,35.5,140.0,36.0&limit=5"
```

### 2.4 MCPサーバーのライブテスト

```fish
cd /path/to/geo-base/mcp

# ローカルサーバーに対してテスト
TILE_SERVER_URL=http://localhost:3000 uv run python tests/live_test.py
```

**期待される出力:**
```
============================================================
🧪 geo-base MCP Server Live Tests
============================================================
📡 Tile Server: http://localhost:3000
🔐 API Token: not configured
🌍 Environment: development

============================================================
🔧 Health Check
============================================================
🌐 Testing: http://localhost:3000/api/health
📡 Status: 200
✅ Server is healthy

============================================================
🔧 List Tilesets
============================================================
📋 tilesets: 4 items
...
✅ Live tests completed!
```

### 2.5 Claude Desktop でのローカルテスト

**~/Library/Application Support/Claude/claude_desktop_config.json**（macOS）:
```json
{
  "mcpServers": {
    "geo-base-local": {
      "command": "/Users/your-username/.local/bin/uv",
      "args": [
        "--directory",
        "/path/to/geo-base/mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "TILE_SERVER_URL": "http://localhost:3000"
      }
    }
  }
}
```

Claude Desktopを再起動後、以下のようなプロンプトでテスト：
- 「タイルセット一覧を表示して」
- 「東京駅の座標を調べて」

---

## 3. リモート本番環境での動作確認

### 3.1 本番環境URL

| サービス | URL |
|---------|-----|
| API (Vercel) | https://geo-base-puce.vercel.app |
| MCP (Fly.io) | https://geo-base-mcp.fly.dev |

### 3.2 APIサーバーの確認

```fish
# ヘルスチェック
curl https://geo-base-puce.vercel.app/api/health

# DBヘルスチェック
curl https://geo-base-puce.vercel.app/api/health/db

# タイルセット一覧
curl https://geo-base-puce.vercel.app/api/tilesets

# フィーチャー検索
curl "https://geo-base-puce.vercel.app/api/features?bbox=139.5,35.5,140.0,36.0&limit=5"

# 特定のタイルセット情報
curl https://geo-base-puce.vercel.app/api/tilesets/{tileset_id}

# TileJSON
curl https://geo-base-puce.vercel.app/api/tilesets/{tileset_id}/tilejson
```

### 3.3 MCPサーバーの確認

```fish
# SSEエンドポイント確認
curl -N https://geo-base-mcp.fly.dev/sse

# Fly.ioステータス確認
cd /path/to/geo-base/mcp
fly status

# Fly.ioログ確認
fly logs
```

### 3.4 MCPサーバーのライブテスト（本番環境）

```fish
cd /path/to/geo-base/mcp

# 本番サーバーに対してテスト
TILE_SERVER_URL=https://geo-base-puce.vercel.app uv run python tests/live_test.py
```

### 3.5 Claude Desktop でのリモートテスト

**設定ファイル:**
```json
{
  "mcpServers": {
    "geo-base-remote": {
      "command": "/Users/your-username/.local/bin/uvx",
      "args": [
        "mcp-proxy",
        "https://geo-base-mcp.fly.dev/sse",
        "--transport=sse"
      ]
    }
  }
}
```

**前提条件:**
```fish
# mcp-proxy をインストール
uv tool install mcp-proxy
```

**テストプロンプト:**
- 「タイルセット一覧を表示して」→ `tool_list_tilesets` を呼び出し
- 「東京駅の座標を調べて」→ `tool_geocode` を呼び出し
- 「緯度35.6812、経度139.7671の住所は？」→ `tool_reverse_geocode` を呼び出し

---

## 4. CRUDエンドポイントのテスト（認証必須）

### 4.1 JWTトークンの取得

Supabase Authでログイン後、セッションから `access_token` を取得します。

### 4.2 タイルセット作成テスト

```fish
# タイルセット作成
curl -X POST https://geo-base-puce.vercel.app/api/tilesets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Test Tileset",
    "type": "vector",
    "format": "pbf",
    "description": "テスト用タイルセット",
    "min_zoom": 0,
    "max_zoom": 14,
    "is_public": false
  }'

# タイルセット更新
curl -X PATCH https://geo-base-puce.vercel.app/api/tilesets/{tileset_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Updated Tileset Name"
  }'

# タイルセット削除
curl -X DELETE https://geo-base-puce.vercel.app/api/tilesets/{tileset_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4.3 フィーチャー作成テスト

```fish
# フィーチャー作成
curl -X POST https://geo-base-puce.vercel.app/api/features \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "tileset_id": "YOUR_TILESET_ID",
    "layer_name": "stations",
    "geometry": {
      "type": "Point",
      "coordinates": [139.7671, 35.6812]
    },
    "properties": {
      "name": "東京駅",
      "type": "station"
    }
  }'

# フィーチャー更新
curl -X PATCH https://geo-base-puce.vercel.app/api/features/{feature_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "properties": {
      "name": "東京駅（更新）"
    }
  }'

# フィーチャー削除
curl -X DELETE https://geo-base-puce.vercel.app/api/features/{feature_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 5. トラブルシューティング

### 5.1 よくある問題

| 問題 | 原因 | 解決策 |
|------|------|--------|
| `Connection refused` | サーバーが起動していない | APIサーバーを起動 |
| `401 Unauthorized` | 認証トークンがない/無効 | 有効なJWTトークンを設定 |
| `403 Forbidden` | 権限がない | タイルセット所有者か確認 |
| `404 Not Found` | リソースが存在しない | ID/URLを確認 |
| `500 Internal Server Error` | サーバーエラー | ログを確認 |

### 5.2 ログの確認

```fish
# Fly.io (MCP サーバー)
cd /path/to/geo-base/mcp
fly logs

# Vercel (API サーバー)
vercel logs https://geo-base-puce.vercel.app
```

### 5.3 デバッグモード

```fish
# MCPサーバーをデバッグモードで起動
cd /path/to/geo-base/mcp
DEBUG=true TILE_SERVER_URL=http://localhost:3000 uv run python server.py
```

---

## 6. デプロイ手順

### 6.1 APIサーバー（Vercel）

```fish
cd /path/to/geo-base/api
vercel --prod
```

### 6.2 MCPサーバー（Fly.io）

```fish
cd /path/to/geo-base/mcp
fly deploy

# シークレットの設定（必要に応じて）
fly secrets set API_TOKEN=your-jwt-token
fly secrets set TILE_SERVER_URL=https://geo-base-puce.vercel.app
```

---

## 7. チェックリスト

### ローカル環境
- [ ] APIサーバーが起動している (`curl http://localhost:3000/api/health`)
- [ ] ユニットテストが全てパス (`uv run pytest -v`)
- [ ] ライブテストが成功 (`uv run python tests/live_test.py`)
- [ ] Claude Desktop で動作確認

### 本番環境
- [ ] APIヘルスチェック成功 (`curl https://geo-base-puce.vercel.app/api/health`)
- [ ] MCPサーバーが稼働 (`fly status`)
- [ ] ライブテスト（本番）が成功
- [ ] Claude Desktop（リモート）で動作確認

---

*最終更新: 2024年12月*
