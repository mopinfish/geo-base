# Redis Cache Setup Guide

このドキュメントでは、geo-base APIのRedisキャッシュの設定方法を説明します。

## 概要

geo-base APIはRedisを使用してタイルデータ、TileJSON、タイルセット情報をキャッシュします。
Redisが利用できない場合は、インメモリキャッシュにフォールバックします。

### キャッシュ対象

| データ種別 | キーパターン | デフォルトTTL |
|-----------|-------------|--------------|
| ベクタータイル | `tile:vector:{id}:{z}:{x}:{y}` | 3600秒 (1時間) |
| ラスタータイル | `tile:raster:{id}:{z}:{x}:{y}` | 3600秒 (1時間) |
| PMTilesタイル | `tile:pmtiles:{id}:{z}:{x}:{y}` | 3600秒 (1時間) |
| TileJSON | `tilejson:{type}:{id}` | 300秒 (5分) |
| タイルセット情報 | `tileset:{id}` | 60秒 (1分) |

---

## ローカル開発環境

### 1. Docker Composeでの起動

```fish
cd /path/to/geo-base/docker

# PostgreSQL + Redis を起動
docker compose up -d

# ログ確認
docker compose logs -f redis

# 停止
docker compose down

# ステータス確認
docker compose ps
```

または、プロジェクトルートから:

```fish
cd /path/to/geo-base

# -f オプションでファイル指定
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml down
```

### 2. 環境変数の設定

`.env` ファイルまたは環境変数で設定します：

```fish
# .env ファイル作成
cat > api/.env << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_KEY_PREFIX=geo-base:

# Cache TTL (seconds)
TILE_CACHE_TTL=3600
TILEJSON_CACHE_TTL=300
TILESET_INFO_CACHE_TTL=60
EOF
```

または、fishシェルで直接設定：

```fish
# Redis設定
set -x REDIS_ENABLED true
set -x REDIS_HOST localhost
set -x REDIS_PORT 6379
set -x REDIS_DB 0
set -x REDIS_KEY_PREFIX "geo-base:"

# キャッシュTTL設定
set -x TILE_CACHE_TTL 3600
set -x TILEJSON_CACHE_TTL 300
set -x TILESET_INFO_CACHE_TTL 60
```

### 3. APIサーバーの起動

```fish
cd api

# 依存関係インストール
uv sync

# サーバー起動
uv run uvicorn main:app --reload --port 8080
```

### 4. 動作確認

```fish
# ヘルスチェック（Redisステータス含む）
curl http://localhost:8080/health

# キャッシュ統計
curl http://localhost:8080/cache/stats
```

### 5. Redis CLIでの確認

```fish
# Redisに接続
docker exec -it geo-base-redis redis-cli

# キー一覧
KEYS geo-base:*

# 特定キーの値
GET geo-base:tileset:your-uuid

# TTL確認
TTL geo-base:tileset:your-uuid

# キャッシュクリア
DEL geo-base:tileset:your-uuid

# 全キャッシュクリア（パターン指定）
# 注意: 本番環境では使用しないでください
redis-cli KEYS "geo-base:*" | xargs redis-cli DEL
```

### 6. Redis Commander (Web UI)

オプションでRedis管理UIを起動できます：

```fish
cd /path/to/geo-base/docker

# Redis Commander を含めて起動
docker compose --profile tools up -d

# ブラウザでアクセス
open http://localhost:8081
```

---

## 本番環境 (Fly.io)

### 1. Fly.io Redis のセットアップ

```fish
# Fly.io にログイン
fly auth login

# Redisアプリを作成
fly redis create

# 接続情報の取得
fly redis status <redis-app-name>
```

### 2. シークレットの設定

```fish
# アプリディレクトリに移動
cd api

# Redis URLを設定
fly secrets set REDIS_URL="redis://default:password@your-redis.upstash.io:6379"

# または個別に設定
fly secrets set REDIS_HOST="your-redis.fly.dev"
fly secrets set REDIS_PORT="6379"
fly secrets set REDIS_PASSWORD="your-password"
fly secrets set REDIS_SSL="true"
```

### 3. fly.toml の確認

`fly.toml` に環境変数が含まれていることを確認：

```toml
[env]
  REDIS_ENABLED = "true"
  REDIS_KEY_PREFIX = "geo-base:"
  TILE_CACHE_TTL = "3600"
  TILEJSON_CACHE_TTL = "300"
  TILESET_INFO_CACHE_TTL = "60"
```

### 4. デプロイ

```fish
fly deploy
```

### 5. 動作確認

```fish
# ヘルスチェック
curl https://geo-base-api.fly.dev/health

# キャッシュ統計
curl https://geo-base-api.fly.dev/cache/stats
```

---

## Upstash Redis (代替オプション)

Fly.io Redis の代わりに、Upstash Redisを使用することもできます。
Upstashは従量課金制で、低トラフィック時のコストを抑えられます。

### 1. Upstash でRedisを作成

1. [Upstash Console](https://console.upstash.com/) にアクセス
2. 「Create Database」をクリック
3. リージョンを選択（Tokyo推奨）
4. 「Create」をクリック

### 2. 接続情報の取得

Upstashダッシュボードから以下を取得：
- REST URL
- REST Token
- Redis URL (TLS)

### 3. 環境変数の設定

```fish
# Fly.io シークレット設定
fly secrets set REDIS_URL="rediss://default:token@your-db.upstash.io:6379"

# または
fly secrets set REDIS_HOST="your-db.upstash.io"
fly secrets set REDIS_PORT="6379"
fly secrets set REDIS_PASSWORD="your-token"
fly secrets set REDIS_SSL="true"
```

---

## 環境変数リファレンス

### Redis接続設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `REDIS_ENABLED` | Redisキャッシュを有効化 | `true` |
| `REDIS_URL` | Redis接続URL（個別設定より優先） | - |
| `REDIS_HOST` | Redisホスト | `localhost` |
| `REDIS_PORT` | Redisポート | `6379` |
| `REDIS_PASSWORD` | Redisパスワード | - |
| `REDIS_DB` | Redisデータベース番号 | `0` |
| `REDIS_SSL` | SSL/TLS接続を使用 | `false` |
| `REDIS_KEY_PREFIX` | キーのプレフィックス | `geo-base:` |
| `REDIS_MAX_CONNECTIONS` | 最大接続数 | `10` |
| `REDIS_SOCKET_TIMEOUT` | ソケットタイムアウト（秒） | `5.0` |
| `REDIS_CONNECT_TIMEOUT` | 接続タイムアウト（秒） | `5.0` |

### キャッシュTTL設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `TILE_CACHE_TTL` | タイルデータのTTL（秒） | `3600` |
| `TILEJSON_CACHE_TTL` | TileJSONのTTL（秒） | `300` |
| `TILESET_INFO_CACHE_TTL` | タイルセット情報のTTL（秒） | `60` |
| `MEMORY_CACHE_MAX_SIZE` | メモリキャッシュの最大エントリ数 | `1000` |
| `MEMORY_CACHE_ENABLED` | メモリキャッシュ（フォールバック）を有効化 | `true` |

### キャッシュ機能フラグ

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `CACHE_VECTOR_TILES` | ベクタータイルキャッシュを有効化 | `true` |
| `CACHE_RASTER_TILES` | ラスタータイルキャッシュを有効化 | `true` |
| `CACHE_PMTILES` | PMTilesキャッシュを有効化 | `true` |
| `CACHE_TILEJSON` | TileJSONキャッシュを有効化 | `true` |

---

## トラブルシューティング

### Redis接続エラー

**症状**: `Redis connection refused` または `Redis unavailable`

**解決策**:
1. Redisサービスが起動しているか確認
   ```fish
   cd docker
   docker compose ps
   ```
2. ポートが正しいか確認
   ```fish
   docker port geo-base-redis
   ```
3. ファイアウォール設定を確認

### SSL接続エラー (本番環境)

**症状**: `SSL: CERTIFICATE_VERIFY_FAILED`

**解決策**:
1. `REDIS_SSL=true` が設定されているか確認
2. Redis URLのスキームが `rediss://` になっているか確認

### キャッシュが効かない

**症状**: 常にキャッシュミス

**解決策**:
1. `REDIS_ENABLED=true` か確認
2. キャッシュ機能フラグを確認
   ```fish
   curl http://localhost:8080/cache/stats
   ```
3. TTLが適切か確認

### メモリ使用量が増加

**症状**: Redisのメモリ使用量が増加し続ける

**解決策**:
1. `maxmemory` と `maxmemory-policy` が設定されているか確認
2. Docker Composeのデフォルト設定では100MBに制限
3. 必要に応じて調整：
   ```fish
   docker exec -it geo-base-redis redis-cli CONFIG SET maxmemory 200mb
   ```

---

## パフォーマンスチューニング

### 推奨設定

**開発環境**:
```
TILE_CACHE_TTL=60          # 短めに設定
MEMORY_CACHE_MAX_SIZE=100  # 小さめに設定
```

**本番環境**:
```
TILE_CACHE_TTL=3600        # 1時間
TILEJSON_CACHE_TTL=300     # 5分
MEMORY_CACHE_MAX_SIZE=1000 # 十分なサイズ
REDIS_MAX_CONNECTIONS=20   # 負荷に応じて調整
```

### モニタリング

```fish
# Redis INFO
docker exec -it geo-base-redis redis-cli INFO

# メモリ使用状況
docker exec -it geo-base-redis redis-cli INFO memory

# ヒット率
docker exec -it geo-base-redis redis-cli INFO stats | grep keyspace
```

---

## 関連ファイル

- `api/lib/redis_client.py` - Redisクライアントモジュール
- `api/lib/tile_cache.py` - タイルキャッシュモジュール
- `api/tests/test_redis_client.py` - Redisクライアントテスト
- `api/tests/test_tile_cache.py` - タイルキャッシュテスト
- `docker/docker-compose.yml` - ローカル開発環境設定
- `docker/postgis-init/` - PostgreSQL初期化スクリプト

---

**作成日**: 2025-12-17  
**最終更新**: 2025-12-17
