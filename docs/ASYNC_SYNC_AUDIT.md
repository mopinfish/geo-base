# async/sync I/O モデル audit と方針提案

> Issue: [#64](https://github.com/mopinfish/geo-base/issues/64)
> 起源: PR [#62](https://github.com/mopinfish/geo-base/pull/62) / [#63](https://github.com/mopinfish/geo-base/pull/63) で Copilot から繰り返し指摘された構造課題

## 問題

`api/lib/routers/` の多くのハンドラが `async def` だが、内部では psycopg2 の **同期 I/O**（`cur.execute()` 等）を直接呼ぶ。FastAPI は `async def` ハンドラをイベントループ上で実行するため、psycopg2 の I/O 中はループがブロックされ、他リクエストの並行処理が滞る。

`def` ハンドラなら FastAPI が threadpool で実行するため、sync DB I/O でも他リクエストをブロックしない。**現状は sync handler 時代より並行性が悪化している**可能性が高い。

## 影響範囲（audit 結果, 2026-05-10）

リポジトリルートから:

```bash
$ grep -rln --include="*.py" "^async def" api/lib/routers/
```

| ファイル | sync DB 呼び出し数（`cur.execute/fetchone/fetchall`）|
|---|---|
| `api/lib/routers/teams.py` | 66 |
| `api/lib/routers/datasources.py` | 35 |
| `api/lib/routers/tilesets.py` | 32 |
| `api/lib/routers/features.py` | 26 |
| `api/lib/routers/tiles/raster.py` | 10 |
| `api/lib/routers/tiles/pmtiles.py` | 6 |
| `api/lib/routers/auth.py` | 6 |
| `api/lib/routers/tiles/dynamic.py` | 2 |
| **合計** | **183** |

`await` の用途内訳:

| 用途 | 件数 | コメント |
|---|---|---|
| `await check_tileset_(write_)access_v2(...)` | 18 | **v2 認可ヘルパが内部で `asyncio.to_thread` を使うために handler を async 化させているもの**。これが **直接の元凶** |
| `await get_auth_provider().*` | 13+ | 真に async な認証 provider メソッド（`api/lib/routers/auth.py`） |
| `await get_email_backend().send(...)` | 1 | `api/lib/routers/teams.py` の招待メール送信 |
| `await get_pmtiles_tile(...)` 等 | 数件 | HTTP fetch（PMTiles リモート読み）|

→ **18/43 = 41% の `await` が v2 認可ヘルパ起因**。残りは genuinely async な処理。

## 4 つの選択肢

### Option A: ハンドラを `def` に戻し、v2 認可ヘルパを sync 化

- v2 ヘルパ（`check_tileset_access_v2` / `check_tileset_write_access_v2`）から `async def` を外し、内部の `asyncio.to_thread` を直接呼び出しに置換
- それを呼ぶ handler の `await` を消し、`async def` → `def` に戻す
- `auth.py` / `teams.py` の email 送信 / `tiles/pmtiles.py` の HTTP fetch など genuinely async な箇所は async のまま（既存通り）

**Pros:**
- FastAPI threadpool で sync handler が動くため、現状の sync DB I/O でも並行性が確保される
- コード変更は機械的で **影響範囲が小さい**（v2 ヘルパ 2 つ + その caller 18 箇所）
- 「DB I/O は sync」という前提を維持し、コードベース全体を一貫させやすい
- cursor lifetime 問題（`with conn.cursor()` 中の `await`）が消滅

**Cons:**
- 真に async な call と sync な call が混在する handler を書く時の判断が必要（が、`auth.py` 等の既存 async handler を見るに既に混在しているので新たな負担ではない）
- 将来 async DB ドライバへ移行する時は再度 async 化が必要

### Option B: `asyncio.to_thread` で全 sync DB 呼び出しをラップ

- 183 箇所の `cur.execute/fetchone/fetchall` を `await asyncio.to_thread(lambda: cur.execute(...))` 等にラップ
- handler は async のまま

**Pros:**
- handler が async のまま、I/O 待ちでイベントループをブロックしない
- 将来 async DB ドライバへ移行しやすい（既に async 化されているので）

**Cons:**
- **書き味が悪い**（変更箇所 183 件、可読性低下）
- ラップ漏れが起きやすい（lint で検出は不可）
- thread 切替コストが per-call で発生（Option A の threadpool 一括処理より低効率）

### Option C: async DB ドライバへ移行（asyncpg / psycopg3 async）

- psycopg2 → asyncpg または psycopg3 (async) に置換
- `cur.execute(...)` → `await cur.execute(...)`
- `api/lib/database.py` の connection pool も async pool に置換

**Pros:**
- 真に async な DB 層になり、handler の async/sync 混在が消える
- 高負荷時のスループットは最良
- 将来性が高い

**Cons:**
- **影響範囲が極大**（`api/lib/database.py` / 全 router / 全 test fixture / すべての SQL 実行箇所）
- 既存 PR [#62](https://github.com/mopinfish/geo-base/pull/62) / [#63](https://github.com/mopinfish/geo-base/pull/63) のテストインフラ（TestClient + dependency_overrides で sync `db_conn` を共有）も大改造
- 移行コスト > 並行性向上のメリットの可能性が高い（geo-base の現状規模では）

### Option D: DB アクセス層に hook を作って統一

- 例: `await db_run(conn, lambda c: c.cursor().execute(...))` のような小ヘルパで全アクセスを統一
- 内部で `asyncio.to_thread` でオフロード

**Pros:**
- 統一インタフェースで lint しやすい / 将来 async DB に切替時の変更点も hook 内に閉じる

**Cons:**
- 既存コードを **183 箇所書き換える**コストは Option B と同等
- プロジェクト固有のヘルパが増えて学習コスト
- 現状の sync 直接呼びと比べて間接層が増える

## 推奨: Option A

理由:

1. **変更コストが圧倒的に小さい**: v2 ヘルパ 2 つ + caller 18 箇所のみ（Option B/C/D は数十〜百単位の変更）
2. **FastAPI の threadpool が既に存在する** — sync handler は I/O 待ちで他リクエストをブロックしない
3. **cursor lifetime の subtle bug を構造的に消滅させる** — `with conn.cursor()` 中の `await` 自体が無くなる
4. **既存コードベースの慣習と整合** — `auth.py` 等の他 router は genuinely async な箇所だけ async def にしている
5. **将来 async DB に移行する時** は Option C を改めて評価する。現時点の規模では Option A で十分

### 実装ステップ案（次の Issue で扱う）

1. `api/lib/auth/__init__.py` の `check_tileset_access_v2` / `check_tileset_write_access_v2` を sync 化（`async def` → `def`、内部の `asyncio.to_thread` を直接呼び出しに置換）
2. 関連 router の handler から `async`/`await` を外す（18 箇所）
   - 例: `api/lib/routers/tilesets.py` の `update_tileset` / `delete_tileset` / `calculate_tileset_bounds`
   - `api/lib/routers/features.py` の `list_features` / `get_feature`
   - `api/lib/routers/datasources.py` の `get_datasource`
   - `api/lib/routers/tiles/*.py` の各 endpoint
3. テストの `@pytest.mark.asyncio` も削除可（v2 ヘルパが sync になるため）。`api/tests/test_auth/test_tile_access_v2.py` / `api/tests/test_auth/test_tileset_write_access_v2.py` は影響大なので別 PR で
4. 整合性確認: pytest 全パス + 手動 E2E

### 着手しない箇所（async のまま維持）

- `api/lib/routers/auth.py` — `get_auth_provider().*` が真に async
- `api/lib/routers/teams.py` の `create_team_invitation` — email 送信が async
- `api/lib/routers/tiles/pmtiles.py` の tile fetch endpoint — HTTP fetch が async

## 開けておく決定事項

- 移行 PR を分割するか単発か:
  - **分割案**: ヘルパ sync 化 → router 1 ファイルずつ revert → 全部済んだら lint clean 確認
  - **単発案**: 機械的な変更なので 1 PR にまとめる
  - 推奨は **2 PR**: (1) ヘルパ sync 化 + caller 全 revert を一度に（変更が機械的）/ (2) テストの `@pytest.mark.asyncio` cleanup
- async DB（Option C）への移行を将来やるか: パフォーマンス計測してから判断する。Option A → 計測 → 必要なら Option C、の順で進める

## 参考

- FastAPI 公式: <https://fastapi.tiangolo.com/async/#in-a-hurry>（"If you don't know, use just `def`"）
- 関連 Issue: [#50](https://github.com/mopinfish/geo-base/issues/50) は本 audit の方針決定後に着手予定（書き込み系を `require_auth_context` + scope check に置換する PR で、v2 ヘルパの sync/async 仕様に依存）
- 起源 PR: [#62](https://github.com/mopinfish/geo-base/pull/62) / [#63](https://github.com/mopinfish/geo-base/pull/63)（Copilot レビューで繰り返し提起）
