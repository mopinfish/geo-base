# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ構成

`geo-base` は地理空間タイルサーバーシステムのモノレポです。3つの独立してデプロイ可能なコンポーネントが、1つの PostGIS データベースを共有します。

- **`api/`** — FastAPI タイルサーバー（Python, `uv` 管理）。**Fly.io** に `geo-base-api.fly.dev` としてデプロイ（旧 Vercel デプロイは廃止済み）。PostGIS から `ST_AsMVT` でベクタータイルを動的生成、`rio-tiler` で COG ラスタータイルを配信、PMTiles にも対応。エントリポイントは `api/lib/main.py` で、`lib/routers/` 配下のルーターを統合。Pydantic モデルは `lib/models/` に配置。
- **`app/`** — Next.js 16（App Router）+ React 19 + Tailwind v4 + shadcn/ui の管理画面。**Vercel** に `geo-base-admin.vercel.app` としてデプロイ。認証は自前の local provider（`AUTH_PROVIDER=local`、Supabase Auth は Issue #72 で 2026-05-10 に廃止）で、`app/src/lib/auth/` の AuthClient が `/api/auth/*` をラップ。API クライアントは `app/src/lib/api.ts`。
- **`mcp/`** — geo-base のツールを Claude Desktop 向けに公開する FastMCP サーバー。**Fly.io** に `geo-base-mcp.fly.dev` としてデプロイ。ツールは `mcp/tools/` 配下（tilesets, features, geocoding, stats, analysis, crud）。`stdio`（ローカル）と `sse`（リモート）の両トランスポートをサポート。
- **`docker/`** — `docker compose` でローカルの PostGIS + Redis を起動。スキーマシード SQL は `docker/postgis-init/` に番号順で配置（`04_auth_schema.sql`: 自前 users / refresh_tokens、`05_teams_schema.sql`: チーム関連、`06_api_keys_schema.sql`: API キー、`09_rls_policies.sql` がローカル開発用 allow-all RLS）。旧 `09_rls_policies.sql.supabase` は Issue #72 / PR #86 で削除予定（PR #86 マージ後は本記述と一致）。
- **`pg/`** — 本番 DB を Fly Machine 上の `postgis/postgis:16-3.4` 単一ノードで運用するための Fly app 設定（`geo-base-pg`）。`Dockerfile` で `docker/postgis-init/` の `01_*.sql` 〜 `06_*.sql` を `/docker-entrypoint-initdb.d/` に焼き込んでいる（`09_rls_policies.sql` は Local 用 allow-all RLS なので本番では除外）。詳細は `docs/POSTGRES_SETUP.md`。
- **`packages/shared/`** — 共有パッケージのスケルトン。
- **`scripts/`** — `setup.sh`, `seed_sample_data.{py,fish}`, `fix_bounds.py` 等。

FastAPI サーバーは **複数環境**（ローカル、Fly.io、レガシーの Vercel）で動作します。`lib/config.py` と `lib/database.py` は `is_vercel` / `is_fly` / `is_serverless` プロパティで分岐します — サーバーレスではリクエストごとの接続、Fly では接続プールを使用。1つのデプロイモデルだけを前提にしないこと。

## ローカルポート（混同注意）

| サービス | ポート | 起動コマンド |
|---|---|---|
| Admin UI (Next.js) | **3000** | `cd app && npm run dev` |
| API (FastAPI) | **8000** | `cd api && uv run uvicorn lib.main:app --reload --port 8000` |
| MCP Server | **8001** | `cd mcp && TILE_SERVER_URL=http://localhost:8000 uv run python server.py` |
| PostGIS | 5432 | `cd docker && docker compose up -d` |
| Redis | 6379 | （同じ compose ファイルで起動） |

古いドキュメント（`TESTING.md`, `setup.sh`, `api/README.md` の例）には API ポートが 3000 と書かれているものがありますが、これは古い情報です。**現行の規約は API=8000、Admin UI=3000**。

## よく使うコマンド

### API (`cd api`)

```fish
uv sync                                         # インストール（uv 管理 venv）
uv sync --extra dev                             # pytest/black/ruff も追加
uv run uvicorn lib.main:app --reload --port 8000

# pytest は専用テスト DB（geo_base_test）が必須。dev DB を破壊しないため、
# TEST_DATABASE_URL を必ず指定する（issue #47）。未指定だと DB 系テストは fail する。
set -x TEST_DATABASE_URL postgresql://postgres:postgres@localhost:5432/geo_base_test
uv run pytest tests/ -v                         # 全テスト
uv run pytest tests/test_validators.py -v       # 単一ファイル
uv run pytest tests/test_retry.py::TestWithDbRetryDecorator -v  # 単一クラス
uv run pytest tests/ --cov=lib --cov-report=term-missing
uv run ruff check .
uv run black .
```

`No module named 'lib'` でインポートに失敗する場合は `PYTHONPATH=.` を設定（または `uv run` 経由で実行すれば自動で解決）。

テスト DB のセットアップ（初回のみ／既存 volume の場合）は `docs/AUTH_E2E_CHECKLIST.md` の「テスト DB（geo_base_test）」セクション参照。

### MCP (`cd mcp`)

```fish
uv sync --extra dev
uv run python server.py                         # stdio モード（デフォルト）
MCP_TRANSPORT=sse uv run python server.py       # SSE モード
uv run pytest -v
TILE_SERVER_URL=https://geo-base-api.fly.dev uv run python tests/live_test.py
uv run ruff check .
uv run black .
```

### Admin UI (`cd app`)

```fish
npm install
npm run dev                                     # Next.js dev サーバー（:3000）
npm run build && npm start                      # 本番ビルド
npm run lint
npm test                                        # Vitest（middleware 等の単体テスト）
npm run test:watch                              # Vitest watch モード
```

### Docker / DB

```fish
cd docker
docker compose up -d                            # postgis + redis
docker compose --profile tools up -d            # + Redis Commander（:8081）
docker compose down
docker compose logs -f postgis
```

### デプロイ

```fish
cd api && fly deploy                            # API → geo-base-api.fly.dev
cd mcp && fly deploy                            # MCP → geo-base-mcp.fly.dev
# Admin UI は push で Vercel が自動デプロイ
```

## 認証モデル

API は自前の **local provider** で認証する（`AUTH_PROVIDER=local` のみサポート）。Supabase Auth provider は 2026-05-10 に Issue #72 / PR #74 で完全廃止された（プラガブル化の枠組み自体は `api/lib/auth/provider.py` に残してあり、将来別 IdP を追加することは可能）。

- `local`: 自前の `users` テーブル + JWT 発行（`api/lib/auth/` パッケージ、初期管理者は `uv run python -m lib.auth.cli create-admin` で作成）

認証必須ルートは `Depends(require_auth)`（ユーザー必須）または `Depends(require_auth_context)`（JWT または API キー）、任意認証は `Depends(get_current_user)` / `Depends(get_auth_context_optional)` を使用。タイルセットには `is_public` フラグがあり、公開読み取りは認証不要だが、書き込みは常に所有者の JWT または API キーが必要。

API キーは別系統の認証パス（Phase 3 / Step 3.3-A）：`lib/routers/api_keys.py` + `lib/models/api_key.py` + `lib/auth/api_key_auth.py`。スキーマは `docker/postgis-init/06_api_keys_schema.sql`。送信ヘッダは `Authorization: Bearer gb_live_...`（`X-API-Key` ではない）。

詳細: `docs/AUTH_SETUP.md`、E2E チェック: `docs/AUTH_E2E_CHECKLIST.md`、認可仕様レビュー: `docs/ACCESS_CONTROL_REVIEW.md`、設計: `docs/superpowers/specs/2026-05-08-pluggable-auth-design.md`（履歴文書）。Supabase からの移行記録は `docs/AUTH_MIGRATION.md`（完了済み）。

## プロジェクト履歴ドキュメント

リポジトリルートの `HANDOVER_*.md` と `ROADMAP_*.md` は過去フェーズの記録（Season 2、Season 3 のフェーズ A〜D、`main.py` の 4,124 行 → 150 行へのリファクタリング等）。コードの分割理由を理解するには有用ですが、**完了済み作業の記録**であり、現行仕様としては扱わないこと。アクティブなフェーズ文書は `HANDOVER_S3.md`（最新）と `ROADMAP_S3.md`。

`geo-base.txt`（約 2.8 MB）はリポジトリのダンプスナップショット — 無視してオリジナルのソースを読むこと。

## アーキテクチャ判断記録

- **`docs/INFRA_MIGRATION_INVESTIGATION.md`**: 2026-05-08 にインフラ集約を検討した経緯と結論。本番 DB と Auth は 2026-05-10 に Supabase から完全離脱した（Fly Postgres 移行 + local provider 一本化）。
- **`docs/POSTGRES_SETUP.md`**: 2026-05-10 に Supabase Free Plan の長期 paused 復旧不能を機に、本番 DB を **Fly Machine 上の自前 PostGIS（`geo-base-pg` app）** に移行した記録と運用手順。Supabase の DB / Auth 双方への依存をこのタイミングで完全に廃止（Issue #72）。
- **`docs/superpowers/specs/2026-05-12-radix-portal-playwright-pitfall.md`**: shadcn/ui (Radix) の `Select` / `AlertDialog` など Portal 系コンポーネントが Playwright headless で `getByRole` selector を間欠的に timeout させる罠と回避策（ネイティブ `<select>` 化、`<AlertDialogAction>` への `data-testid` 付与）。新規 E2E を書く際は最初から testid 設計にすること。

## 知っておくべき規約

- Python: ruff + black、行長 **100**、ターゲット `py311`。`pytest` は各 `pyproject.toml` で設定済み。`api/` では `addopts = "-v --tb=short"`。
- ドキュメントのシェル例は **fish** 構文（`set -x VAR value`）を使用（ユーザーのシェルに合わせて）。CI 用にスクリプト化する場合は bash に変換すること。
- Python パッケージマネージャは **`uv` のみサポート** — `pip` を直接使わないこと。
- ベクタータイルは PostGIS から動的生成（事前焼き込みではない）。動的タイルルーターは `api/lib/routers/tiles/dynamic.py`。キャッシュ層は `lib/cache.py`（Redis）+ `lib/tile_cache.py`（タイル特化）。
- バッチフィーチャー操作（GeoJSON/CSV エクスポート、`dry_run` 対応の一括更新/削除）は `lib/batch.py` + `lib/routers/batch_features.py`。

## ドキュメント生成方針

本プロジェクトのドキュメント（README、コメント、引き継ぎ文書等）は **基本的に日本語で生成すること**。コード内の識別子・型注釈・docstring の技術用語は英語のままで構わない。
