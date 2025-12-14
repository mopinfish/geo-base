# geo-base MCP サーバー

geo-base タイルサーバー用の MCP (Model Context Protocol) サーバーです。Claude Desktop から geo-base タイルサーバーの地理空間データにアクセスできるようになります。

## 機能一覧

### タイルセットツール
- **list_tilesets**: 利用可能なタイルセット一覧を取得（ベクター、ラスター、PMTiles）
- **get_tileset**: 特定のタイルセットの詳細情報を取得
- **get_tileset_tilejson**: マップクライアント連携用のTileJSONメタデータを取得

### フィーチャーツール
- **search_features**: bbox、レイヤー、フィルター条件で地理フィーチャーを検索
- **get_feature**: 特定のフィーチャーの詳細情報を取得
- **get_features_in_tile**: 特定のマップタイル内のフィーチャーを取得

### ジオコーディングツール
- **geocode**: 住所・地名から座標を取得（ジオコーディング）
- **reverse_geocode**: 座標から住所を取得（逆ジオコーディング）

### 統計ツール
- **get_tileset_stats**: タイルセットの統計情報を取得（フィーチャー数、ジオメトリタイプ分布）
- **get_feature_distribution**: フィーチャーのジオメトリタイプ分布を取得
- **get_layer_stats**: レイヤー別の統計情報を取得
- **get_area_stats**: 指定エリアの統計情報を取得

### 空間分析ツール
- **analyze_area**: 指定エリアの包括的な空間分析（密度、クラスタリング）
- **calculate_distance**: 2点間の距離を計算（ハバーサイン公式）
- **find_nearest_features**: 指定地点の近傍フィーチャーを検索
- **get_buffer_zone_features**: リングバッファ（ドーナツ形状）内のフィーチャーを取得

### CRUDツール（認証必須）
- **create_tileset**: 新しいタイルセットを作成
- **update_tileset**: 既存のタイルセットを更新
- **delete_tileset**: タイルセットと関連フィーチャーを削除
- **create_feature**: タイルセットに新しいフィーチャーを作成
- **update_feature**: 既存のフィーチャーを更新
- **delete_feature**: フィーチャーを削除

### ユーティリティツール
- **get_tile_url**: 特定のマップタイルのURLを生成
- **health_check**: タイルサーバーのヘルスステータスを確認
- **get_server_info**: MCPサーバーの設定情報を取得

## インストール

### 前提条件
- Python 3.11以上
- uv（Pythonパッケージマネージャー）
- Claude Desktop（MCPサーバー利用時）

### セットアップ

```fish
# mcpディレクトリに移動
cd mcp

# 環境ファイルを作成
cp .env.example .env

# .envを編集してTILE_SERVER_URLを設定
# ローカル開発: http://localhost:3000
# 本番環境: https://geo-base-puce.vercel.app

# 依存関係をインストール
uv sync

# サーバーを起動（テスト用）
uv run python server.py
```

## 設定

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `TILE_SERVER_URL` | `http://localhost:3000` | geo-baseタイルサーバーのベースURL |
| `API_TOKEN` | (なし) | 認証リクエスト用のJWTトークン |
| `SERVER_NAME` | `geo-base` | MCPサーバー名 |
| `SERVER_VERSION` | `1.0.0` | MCPサーバーバージョン |
| `ENVIRONMENT` | `development` | 環境（development/production） |
| `HTTP_TIMEOUT` | `30.0` | HTTPリクエストタイムアウト（秒） |
| `DEBUG` | `false` | デバッグモードの有効化 |
| `LOG_LEVEL` | `INFO` | ログレベル（DEBUG/INFO/WARNING/ERROR） |
| `RETRY_MAX_ATTEMPTS` | `3` | リトライ最大試行回数 |
| `RETRY_MIN_WAIT` | `1` | リトライ最小待機時間（秒） |
| `RETRY_MAX_WAIT` | `10` | リトライ最大待機時間（秒） |

### Claude Desktop の設定

Claude Desktop の設定ファイルに以下を追加してください：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### ローカルモード（stdio）

```json
{
  "mcpServers": {
    "geo-base": {
      "command": "/Users/your-username/.local/bin/uv",
      "args": [
        "--directory",
        "/path/to/geo-base/mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "TILE_SERVER_URL": "https://geo-base-puce.vercel.app"
      }
    }
  }
}
```

> **注意**: `uv` コマンドのフルパスを使用してください。`which uv` で確認できます。

#### リモートモード（SSE経由）

```json
{
  "mcpServers": {
    "geo-base-remote": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "https://geo-base-mcp.fly.dev/sse",
        "--transport=sse"
      ]
    }
  }
}
```

> **注意**: リモート SSE エンドポイントに接続するには `mcp-proxy` が必要です。以下でインストールしてください：
> ```fish
> uv tool install mcp-proxy
> ```

## 使用例

Claude Desktop で設定後、自然言語で geo-base タイルサーバーと対話できます：

### タイルセット一覧
```
利用可能なタイルセットを表示して
```

### フィーチャー検索
```
東京エリア（bbox: 139.5,35.5,140.0,36.0）のフィーチャーを検索して
```

### タイルセット情報の取得
```
タイルセット {tileset_id} の詳細を教えて
```

### ジオコーディング
```
東京駅の座標を調べて
```

### 逆ジオコーディング
```
緯度35.6812、経度139.7671の住所は？
```

### 統計情報
```
タイルセット {tileset_id} の統計情報を表示して
```

### 空間分析
```
bbox 139.5,35.5,140.0,36.0 のエリアを分析して
```

### 距離計算
```
東京駅と渋谷駅の距離を計算して
```

### 近傍検索
```
緯度35.6812、経度139.7671から半径1km以内のフィーチャーを探して
```

### タイルセット作成（認証必須）
```
「東京の駅」という名前で「東京都内の鉄道駅」という説明のベクタータイルセットを作成して
```

### フィーチャー作成（認証必須）
```
タイルセット {tileset_id} に座標 [139.7671, 35.6812] で東京駅のポイントフィーチャーを追加して
```

### ヘルスチェック
```
タイルサーバーが正常に動作しているか確認して
```

## デプロイ（Fly.io）

Fly.io を使用したリモートデプロイの手順：

### 前提条件

1. [Fly.io アカウント](https://fly.io/signup)
2. [Fly CLI](https://fly.io/docs/flyctl/install/) のインストール

### 初回セットアップ

```fish
# Fly CLI をインストール（未インストールの場合）
curl -L https://fly.io/install.sh | sh

# Fly.io にログイン
fly auth login

# mcp ディレクトリに移動
cd mcp

# アプリを作成（初回のみ）
fly launch --no-deploy

# シークレットを設定（認証APIアクセス用、オプション）
fly secrets set API_TOKEN=your-jwt-token

# デプロイ
fly deploy
```

### デプロイの更新

```fish
cd mcp
fly deploy
```

### トランスポートモード

MCP サーバーは複数のトランスポートモードをサポートしています：

| モード | 環境変数 | 用途 |
|--------|----------|------|
| `stdio` | `MCP_TRANSPORT=stdio` | ローカル Claude Desktop（デフォルト） |
| `sse` | `MCP_TRANSPORT=sse` | Fly.io 経由のリモート接続 |
| `streamable-http` | `MCP_TRANSPORT=streamable-http` | 代替 HTTP トランスポート |

### モニタリング

```fish
# ログを表示
fly logs

# アプリのステータスを確認
fly status

# ダッシュボードを開く
fly dashboard
```

## 開発

### テストの実行

```fish
# 開発依存関係をインストール
uv sync --extra dev

# テストを実行
uv run pytest

# 詳細表示でテストを実行
uv run pytest -v

# ライブテスト（本番サーバーに対して実行）
TILE_SERVER_URL=https://geo-base-puce.vercel.app uv run python tests/live_test.py
```

### コードフォーマット

```fish
# コードをフォーマット
uv run black .

# コードをリント
uv run ruff check .
```

## アーキテクチャ

```
mcp/
├── server.py          # メインエントリーポイント（MCPサーバー）
├── config.py          # 設定管理
├── logger.py          # ログユーティリティ
├── errors.py          # エラーハンドリング
├── retry.py           # リトライ機能
├── validators.py      # 入力バリデーション
├── tools/
│   ├── tilesets.py    # タイルセットツール
│   ├── features.py    # フィーチャーツール
│   ├── geocoding.py   # ジオコーディングツール
│   ├── stats.py       # 統計ツール
│   ├── analysis.py    # 空間分析ツール
│   ├── crud_tilesets.py  # タイルセットCRUD
│   └── crud_features.py  # フィーチャーCRUD
├── tests/
│   ├── test_*.py      # ユニットテスト
│   └── live_test.py   # ライブテスト
├── Dockerfile         # Fly.ioデプロイ用
├── fly.toml           # Fly.io設定
└── pyproject.toml     # Python依存関係
```

## エラーハンドリング

MCPサーバーは以下のエラーコードを返します：

| コード | 説明 |
|--------|------|
| `VALIDATION_ERROR` | 入力パラメータが無効 |
| `NOT_FOUND` | リソースが見つからない |
| `UNAUTHORIZED` | 認証が必要 |
| `FORBIDDEN` | アクセス権限がない |
| `HTTP_ERROR` | HTTPエラー（4xx/5xx） |
| `NETWORK_ERROR` | ネットワークエラー |
| `UNKNOWN_ERROR` | 予期しないエラー |

## ライセンス

MIT License
