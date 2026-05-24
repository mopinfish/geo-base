# geo-base Season 3 引き継ぎドキュメント - Step 3.2-B

**更新日**: 2025-12-17  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**現在のブランチ**: `develop`

---

## 1. 現在のシステム状況

### 1.1 デプロイ状況

| コンポーネント | ステータス | URL | バージョン |
|---------------|-----------|-----|-----------|
| API Server (Fly.io) | ✅ 稼働中 | https://geo-base-api.fly.dev | 0.4.1 → **0.4.2** |
| MCP Server (Fly.io) | ✅ 稼働中 | https://geo-base-mcp.fly.dev | 0.2.5 |
| Admin UI (Vercel) | ✅ 稼働中 | https://geo-base-admin.vercel.app | 0.4.0 |

### 1.2 Season 3 進捗サマリー

| フェーズ | ステップ | 内容 | ステータス |
|---------|---------|------|-----------|
| Phase 1 | Step 3.1-A | Fly.io移行準備（Dockerfile, fly.toml） | ✅ 完了 |
| Phase 1 | Step 3.1-B | API移行・動作確認 | ✅ 完了 |
| Phase 1 | Step 3.1-C | COGサポート | ✅ 完了 |
| Phase 1 | Step 3.1-D | ラスター分析 | ✅ 完了 |
| Phase 1 | Step 3.1-E | Admin UI更新 | ✅ 完了 |
| - | main.pyリファクタリング | 4,124行 → 150行にモジュール分割 | ✅ 完了 |
| Phase 2 | Step 3.2-A | バリデーション強化 | ✅ 完了 |
| **Phase 2** | **Step 3.2-B** | **リトライ機能統合** | ✅ **完了** |
| Phase 2 | Step 3.2-C | Redisキャッシュ導入 | 🔜 次のステップ |
| Phase 2 | Step 3.2-D | バッチ処理最適化 | 📋 計画中 |

---

## 2. 今回完了した作業: Step 3.2-B リトライ機能統合

### 2.1 概要

API側にリトライユーティリティを実装し、データベース操作の信頼性を向上させました。

### 2.2 実装内容

#### Step 3.2-B.1: リトライユーティリティ

**新規ファイル**: `api/lib/retry.py` (~550行)

主要コンポーネント:

1. **RetryConfig** - リトライ設定データクラス
   - `max_attempts`: 最大リトライ回数（デフォルト: 3）
   - `base_delay`: 基本遅延時間（デフォルト: 0.5秒）
   - `max_delay`: 最大遅延時間（デフォルト: 10秒）
   - `exponential_base`: 指数バックオフ係数
   - `jitter`: ランダム遅延の有無
   - `retryable_exceptions`: リトライ対象例外
   - `on_retry`: リトライ時コールバック

2. **ヘルパー関数**
   - `is_retryable_error(error)`: エラーがリトライ可能か判定
   - `calculate_delay(attempt, config)`: 遅延時間を計算（指数バックオフ）
   - `RETRYABLE_ERROR_PATTERNS`: リトライ可能なエラーパターンリスト

3. **デコレータ**
   - `@with_retry()`: 汎用リトライデコレータ
   - `@with_db_retry()`: DB操作専用リトライデコレータ

4. **実行関数**
   - `execute_with_retry(operation, config)`: 関数をリトライ付きで実行
   - `execute_db_operation(operation, config)`: DB操作専用

5. **コンテキストマネージャ**
   - `RetryContext`: リトライループ用

6. **クラス**
   - `RetryableOperation`: 状態を持つリトライ可能操作の基底クラス

#### Step 3.2-B.2: DBヘルパー関数

**新規ファイル**: `api/lib/db_helpers.py` (~400行)

リトライ対応のDB操作ヘルパー:

1. **クエリ実行**
   - `execute_query(conn, query, params)`: リトライ付きクエリ実行
   - `execute_query_with_columns(conn, query)`: カラム名付き結果取得
   - `execute_query_as_dicts(conn, query)`: 辞書形式で結果取得

2. **トランザクション**
   - `execute_transaction(conn, func)`: トランザクション内でリトライ
   - `execute_insert(conn, query)`: INSERT with RETURNING
   - `execute_update(conn, query)`: UPDATE with row count
   - `execute_delete(conn, query)`: DELETE with row count

3. **バッチ操作**
   - `execute_batch(conn, query, params_list)`: executemanyのリトライ版
   - `execute_values(conn, query, params_list)`: execute_valuesのリトライ版

4. **便利関数**
   - `get_tileset_by_id(conn, id)`: タイルセット取得
   - `check_tileset_owner(conn, id, user_id)`: 所有者チェック
   - `count_features(conn, tileset_id)`: フィーチャー数カウント

### 2.3 テストコード

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `test_retry.py` | 51 | リトライユーティリティテスト |
| `test_db_helpers.py` | 29 | DBヘルパーテスト |

**新規テスト合計**: 80テスト

**テストカバレッジ内容**:
- RetryConfig設定テスト
- is_retryable_error判定テスト
- calculate_delay計算テスト
- デコレータテスト（with_retry, with_db_retry）
- 実行関数テスト
- コンテキストマネージャテスト
- DBヘルパー各関数のテスト

### 2.4 リトライ可能なエラーパターン

```python
RETRYABLE_ERROR_PATTERNS = [
    "ssl connection has been closed unexpectedly",
    "connection reset by peer",
    "connection timed out",
    "server closed the connection unexpectedly",
    "could not receive data from server",
    "network is unreachable",
    "connection refused",
    "could not connect to server",
    "the database system is starting up",
    "connection already closed",
    "cursor already closed",
    "no connection to the server",
    "connection terminated",
    "connection lost",
    "deadlock detected",
    "could not serialize access",
    "statement timeout",
]
```

---

## 3. 使用方法

### 3.1 デコレータを使用

```python
from lib.retry import with_db_retry

@with_db_retry(max_attempts=3, base_delay=0.5)
def get_tilesets(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM tilesets")
        return cur.fetchall()
```

### 3.2 DBヘルパーを使用

```python
from lib.db_helpers import execute_query, execute_transaction

# シンプルなクエリ
rows = execute_query(conn, "SELECT * FROM tilesets WHERE type = %s", ("vector",))

# トランザクション
def create_tileset_with_features(conn):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO tilesets (...) VALUES (...) RETURNING id")
        tileset_id = cur.fetchone()[0]
        cur.execute("INSERT INTO features (...) VALUES (...)")
    return tileset_id

tileset_id = execute_transaction(conn, create_tileset_with_features)
```

### 3.3 環境変数で設定

```fish
# リトライ設定
set -x RETRY_MAX_ATTEMPTS 5
set -x RETRY_BASE_DELAY 1.0
set -x RETRY_MAX_DELAY 30
```

---

## 4. ファイル一覧

### 追加・更新ファイル

```
api/
├── lib/
│   ├── retry.py              # 新規 (550行) - リトライユーティリティ
│   └── db_helpers.py         # 新規 (400行) - DBヘルパー関数
└── tests/
    ├── test_retry.py         # 新規 (500行) - リトライテスト
    ├── test_db_helpers.py    # 新規 (320行) - DBヘルパーテスト
    └── README.md             # 更新 - テストドキュメント
```

**合計**: 約1,770行の新規コード、80テストケース

---

## 5. 次のステップ: Step 3.2-C Redisキャッシュ導入

### 5.1 タスク一覧

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| Redis/Upstash設定 | Fly.ioでのRedis接続設定 | 0.5日 |
| タイルキャッシュ | MVT/ラスタータイルのキャッシュ | 1.5日 |
| TileJSONキャッシュ | メタデータのキャッシュ | 0.5日 |
| キャッシュ無効化 | データ更新時の自動クリア | 1日 |
| テスト追加 | キャッシュテスト | 0.5日 |

### 5.2 計画

1. **Upstash Redis** または **Fly.io Redis** の選定
2. `api/lib/cache.py` の拡張
3. タイル生成エンドポイントへのキャッシュ統合
4. キャッシュヒット率のモニタリング

---

## 6. テスト実行方法

```fish
cd api

# 全テスト実行
uv run pytest tests/ -v

# 新規追加テストのみ
uv run pytest tests/test_retry.py tests/test_db_helpers.py -v

# カバレッジ付き
uv run pytest tests/ --cov=lib --cov-report=term-missing
```

**期待される結果**:
```
212 passed in X.XXs
```

---

## 7. デプロイ手順

```fish
cd /path/to/geo-base

# zipを解凍して上書き
unzip -o ~/Downloads/geo-base-step3.2-B.zip -d .

# テスト実行確認
cd api
uv run pytest tests/ -v

# コミット & プッシュ
cd ..
git add .
git commit -m "feat(api): Step 3.2-B - リトライ機能統合

Step 3.2-B.1: リトライユーティリティ
- api/lib/retry.py: RetryConfig, with_retry, with_db_retry デコレータ
- 指数バックオフ、ジッター、リトライ可能エラー判定

Step 3.2-B.2: DBヘルパー関数
- api/lib/db_helpers.py: リトライ対応のDB操作関数
- execute_query, execute_transaction, execute_batch等

テストコード:
- api/tests/test_retry.py: 51テスト
- api/tests/test_db_helpers.py: 29テスト
- 合計80テスト追加（総数212テスト）"

git push origin develop

# Fly.ioデプロイ（必要に応じて）
cd api
fly deploy
```

---

## 8. 技術メモ

### 8.1 リトライ戦略

- **指数バックオフ**: `delay = base_delay * (2 ^ attempt)`
- **ジッター**: ±10%のランダム変動でサンダリングハード問題を回避
- **最大遅延**: 設定値でキャップ

### 8.2 リトライ対象エラー

DB操作では以下の例外タイプをリトライ:
- `psycopg2.OperationalError`
- `psycopg2.InterfaceError`
- `psycopg2.InternalError`（デッドロック等）

以下はリトライしない:
- `psycopg2.ProgrammingError`（SQLエラー）
- `psycopg2.DataError`（データ型エラー）
- `psycopg2.IntegrityError`（制約違反）

### 8.3 既存のdatabase.pyとの関係

`api/lib/database.py` には既に接続レベルのリトライが実装されています。
今回追加したリトライは操作レベルのもので、接続確立後の一時的なエラーに対応します。

```
[クライアント] → [retry.py/db_helpers.py] → [database.py] → [PostgreSQL]
                    操作レベルリトライ        接続レベルリトライ
```

---

## 9. 参考リソース

### プロジェクトドキュメント

| ファイル | 説明 |
|---------|------|
| `/mnt/project/ROADMAP_S3.md` | Season 3 完全ロードマップ |
| `/mnt/project/HANDOVER_S3.md` | 前回の引き継ぎ（Step 3.2-A） |
| `/mnt/project/MCP_BEST_PRACTICES.md` | MCPサーバー実装ベストプラクティス |
| `api/tests/README.md` | テスト実行ガイド |

### 外部参考

- [tenacity](https://tenacity.readthedocs.io/) - Pythonリトライライブラリ
- [psycopg2 Exceptions](https://www.psycopg.org/docs/errors.html)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)

---

**作成者**: Claude (Anthropic)  
**完了日**: 2025-12-17  
**次回作業**: Phase 2 Step 3.2-C（Redisキャッシュ導入）
