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

### ジオコーディングツール
- **geocode**: 住所・地名から座標を取得（ジオコーディング）
- **reverse_geocode**: 座標から住所を取得（逆ジオコーディング）

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
| `SERVER_VERSION` | `0.1.0` | MCPサーバーバージョン |
| `ENVIRONMENT` | `development` | 環境（development/production） |
| `HTTP_TIMEOUT` | `30.0` | HTTPリクエストタイムアウト（秒） |
| `DEBUG` | `false` | デバッグモードの有効化 |

### Claude Desktop の設定

Claude Desktop の設定ファイルに以下を追加してください：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "geo-base": {
      "command": "uv",
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

### Claude Desktop からリモート MCP サーバーへの接続

Fly.io にデプロイ後、Claude Desktop の設定を更新してリモートサーバーを使用します：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

## API リファレンス

### タイルセットツール

#### `list_tilesets(type?, is_public?)`
タイルサーバーから利用可能なタイルセット一覧を取得します。

**パラメータ:**
- `type`（オプション）: タイプでフィルタリング（'vector', 'raster', 'pmtiles'）
- `is_public`（オプション）: 公開/非公開ステータスでフィルタリング

**戻り値:** id、name、description、type、format、ズーム範囲を含むタイルセットのリスト

#### `get_tileset(tileset_id)`
特定のタイルセットの詳細情報を取得します。

**パラメータ:**
- `tileset_id`: タイルセットのUUID

**戻り値:** bounds、center、metadataを含むタイルセットの詳細

#### `get_tileset_tilejson(tileset_id)`
タイルセットのTileJSONメタデータを取得します。

**パラメータ:**
- `tileset_id`: タイルセットのUUID

**戻り値:** tiles URL、bounds、zoom range、vector_layersを含むTileJSONオブジェクト

### フィーチャーツール

#### `search_features(bbox?, layer?, filter?, limit?, tileset_id?)`
地理フィーチャーを検索します。

**パラメータ:**
- `bbox`（オプション）: バウンディングボックス "minx,miny,maxx,maxy"（WGS84）
- `layer`（オプション）: レイヤー名フィルター
- `filter`（オプション）: プロパティフィルター "key=value"
- `limit`（オプション）: 返すフィーチャーの最大数（デフォルト: 100）
- `tileset_id`（オプション）: 特定のタイルセットに限定

**戻り値:** ジオメトリとプロパティを含むGeoJSONフィーチャーのリスト

#### `get_feature(feature_id)`
特定のフィーチャーの詳細情報を取得します。

**パラメータ:**
- `feature_id`: フィーチャーのUUID

**戻り値:** 完全なジオメトリとプロパティを含むGeoJSONフィーチャー

### ジオコーディングツール

#### `geocode(query, limit?, country_codes?, language?)`
住所または地名を地理座標に変換します。

**パラメータ:**
- `query`: 検索する住所または地名（例: "東京駅", "Tokyo Tower"）
- `limit`（オプション）: 最大結果数（1-50、デフォルト: 5）
- `country_codes`（オプション）: ISO 3166-1 国コード（例: "jp", "jp,us"）
- `language`（オプション）: 結果の言語（デフォルト: "ja"）

**戻り値:** 座標、住所詳細、boundsを含むマッチした場所のリスト

#### `reverse_geocode(latitude, longitude, zoom?, language?)`
地理座標を住所に変換します。

**パラメータ:**
- `latitude`: 緯度（10進度、WGS84）
- `longitude`: 経度（10進度、WGS84）
- `zoom`（オプション）: 詳細レベル 0-18（デフォルト: 18、建物レベル）
- `language`（オプション）: 結果の言語（デフォルト: "ja"）

**戻り値:** 住所コンポーネント、表示名、boundsを含む場所情報

### CRUD ツール

> **注意:** すべてのCRUDツールは認証が必要です。有効なJWTトークンを `API_TOKEN` 環境変数に設定してください。

#### `create_tileset(name, type, format, description?, ...)`
新しいタイルセットを作成します。

**パラメータ:**
- `name`: タイルセット名（必須）
- `type`: タイルセットタイプ（'vector', 'raster', 'pmtiles'）
- `format`: タイルフォーマット（'pbf', 'png', 'jpg', 'webp', 'geojson'）
- `description`（オプション）: タイルセットの説明
- `min_zoom`（オプション）: 最小ズームレベル（0-22、デフォルト: 0）
- `max_zoom`（オプション）: 最大ズームレベル（0-22、デフォルト: 22）
- `bounds`（オプション）: バウンディングボックス [west, south, east, north]
- `center`（オプション）: 中心点 [longitude, latitude]
- `attribution`（オプション）: 帰属テキスト
- `is_public`（オプション）: 公開設定（デフォルト: false）
- `metadata`（オプション）: 追加メタデータオブジェクト

**戻り値:** id、name、type、formatなどを含む作成されたタイルセットオブジェクト

#### `update_tileset(tileset_id, name?, description?, ...)`
既存のタイルセットを更新します。

**パラメータ:**
- `tileset_id`: 更新するタイルセットのUUID
- その他のパラメータはすべてオプションで、指定された場合のみ更新

**戻り値:** 更新されたタイルセットオブジェクト

#### `delete_tileset(tileset_id)`
タイルセットとそのすべてのフィーチャーを削除します。

**パラメータ:**
- `tileset_id`: 削除するタイルセットのUUID

**戻り値:** 成功メッセージまたはエラー

#### `create_feature(tileset_id, geometry, properties?, layer_name?)`
タイルセットに新しいフィーチャーを作成します。

**パラメータ:**
- `tileset_id`: 親タイルセットのUUID
- `geometry`: GeoJSONジオメトリオブジェクト（Point, LineString, Polygon など）
- `properties`（オプション）: フィーチャープロパティ（キー・バリューペア）
- `layer_name`（オプション）: レイヤー名（デフォルト: "default"）

**戻り値:** GeoJSON Feature オブジェクトとして作成されたフィーチャー

#### `update_feature(feature_id, geometry?, properties?, layer_name?)`
既存のフィーチャーを更新します。

**パラメータ:**
- `feature_id`: 更新するフィーチャーのUUID
- その他のパラメータはすべてオプションで、指定された場合のみ更新

**戻り値:** GeoJSON Feature オブジェクトとして更新されたフィーチャー

#### `delete_feature(feature_id)`
フィーチャーを削除します。

**パラメータ:**
- `feature_id`: 削除するフィーチャーのUUID

**戻り値:** 成功メッセージまたはエラー

## ライセンス

MIT ライセンス - 詳細は LICENSE ファイルを参照してください。
