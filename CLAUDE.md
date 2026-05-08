# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ構成

`geo-base` は地理空間タイルサーバーシステムのモノレポです。3つの独立してデプロイ可能なコンポーネントが、1つの PostGIS データベースを共有します。

- **`api/`** — FastAPI タイルサーバー（Python, `uv` 管理）。**Fly.io** に `geo-base-api.fly.dev` としてデプロイ（旧 Vercel デプロイは廃止済み）。PostGIS から `ST_AsMVT` でベクタータイルを動的生成、`rio-tiler` で COG ラスタータイルを配信、PMTiles にも対応。エントリポイントは `api/lib/main.py` で、`lib/routers/` 配下のルーターを統合。Pydantic モデルは `lib/models/` に配置。
- **`app/`** — Next.js 16（App Router）+ React 19 + Tailwind v4 + shadcn/ui の管理画面。**Vercel** に `geo-base-admin.vercel.app` としてデプロイ。認証は Supabase 経由。API クライアントは `app/src/lib/api.ts`。
- **`mcp/`** — geo-base のツールを Claude Desktop 向けに公開する FastMCP サーバー。**Fly.io** に `geo-base-mcp.fly.dev` としてデプロイ。ツールは `mcp/tools/` 配下（tilesets, features, geocoding, stats, analysis, crud）。`stdio`（ローカル）と `sse`（リモート）の両トランスポートをサポート。
- **`docker/`** — `docker compose` でローカルの PostGIS + Redis を起動。スキーマシード SQL は `docker/postgis-init/` に番号順で配置（`04_rls_policies.sql` がローカル用、`04_rls_policies.sql.supabase` が Supabase 用）。
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
uv run pytest tests/ -v                         # 全テスト
uv run pytest tests/test_validators.py -v       # 単一ファイル
uv run pytest tests/test_retry.py::TestWithDbRetryDecorator -v  # 単一クラス
uv run pytest tests/ --cov=lib --cov-report=term-missing
uv run ruff check .
uv run black .
```

`No module named 'lib'` でインポートに失敗する場合は `PYTHONPATH=.` を設定（または `uv run` 経由で実行すれば自動で解決）。

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
```

`app/` には **テストランナーは未設定**。

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

API は **Supabase JWT** 検証を使用（`api/lib/auth.py` の `verify_jwt_token`）。保護エンドポイントには `SUPABASE_JWT_SECRET` の設定が必須。認証必須ルートは `Depends(get_current_user)`、任意認証は `Depends(get_optional_user)` を使用。Admin UI はセッション管理に `@supabase/ssr` を採用。タイルセットには `is_public` フラグがあり、公開読み取りは認証不要だが、書き込みは常に所有者の JWT が必要。

API キーは別系統の認証パス（Phase 3 / Step 3.3 で追加）：`lib/routers/api_keys.py` + `lib/models/api_key.py`。スキーマは `docker/postgis-init/06_api_keys_schema.sql`。

## プロジェクト履歴ドキュメント

リポジトリルートの `HANDOVER_*.md` と `ROADMAP_*.md` は過去フェーズの記録（Season 2、Season 3 のフェーズ A〜D、`main.py` の 4,124 行 → 150 行へのリファクタリング等）。コードの分割理由を理解するには有用ですが、**完了済み作業の記録**であり、現行仕様としては扱わないこと。アクティブなフェーズ文書は `HANDOVER_S3.md`（最新）と `ROADMAP_S3.md`。

`geo-base.txt`（約 2.8 MB）はリポジトリのダンプスナップショット — 無視してオリジナルのソースを読むこと。

## アーキテクチャ判断記録

- **`docs/INFRA_MIGRATION_INVESTIGATION.md`**: 2026-05-08 に Cloudflare 一本化移行を検討した結果。**当面は現状の Vercel/Fly.io/Supabase 構成を維持**することを決定。Phase 3（team/role）の実装は Supabase 依存を極力薄くして、将来の移行可能性を残す方針。

## 知っておくべき規約

- Python: ruff + black、行長 **100**、ターゲット `py311`。`pytest` は各 `pyproject.toml` で設定済み。`api/` では `addopts = "-v --tb=short"`。
- ドキュメントのシェル例は **fish** 構文（`set -x VAR value`）を使用（ユーザーのシェルに合わせて）。CI 用にスクリプト化する場合は bash に変換すること。
- Python パッケージマネージャは **`uv` のみサポート** — `pip` を直接使わないこと。
- ベクタータイルは PostGIS から動的生成（事前焼き込みではない）。動的タイルルーターは `api/lib/routers/tiles/dynamic.py`。キャッシュ層は `lib/cache.py`（Redis）+ `lib/tile_cache.py`（タイル特化）。
- バッチフィーチャー操作（GeoJSON/CSV エクスポート、`dry_run` 対応の一括更新/削除）は `lib/batch.py` + `lib/routers/batch_features.py`。

## ドキュメント生成方針

本プロジェクトのドキュメント（README、コメント、引き継ぎ文書等）は **基本的に日本語で生成すること**。コード内の識別子・型注釈・docstring の技術用語は英語のままで構わない。
