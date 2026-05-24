# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ構成

`geo-base` は地理空間タイルサーバーシステムのモノレポです。3つの独立してデプロイ可能なコンポーネントが、1つの PostGIS データベースを共有します。

- **`api/`** — FastAPI タイルサーバー（Python, `uv`）。Fly.io に `geo-base-api.fly.dev` としてデプロイ。PostGIS から `ST_AsMVT` でベクタータイルを動的生成、`rio-tiler` で COG ラスタータイルを配信、PMTiles にも対応。エントリポイント `api/lib/main.py`、ルーター `lib/routers/`、Pydantic モデル `lib/models/`。
- **`app/`** — Next.js 16（App Router）+ React 19 + Tailwind v4 + shadcn/ui の管理画面。Vercel にデプロイ（`geo-base-admin.vercel.app`）。認証は local provider（`AUTH_PROVIDER=local`）、API クライアントは `app/src/lib/api.ts`。
- **`mcp/`** — FastMCP サーバー（Fly.io: `geo-base-mcp.fly.dev`）。ツールは `mcp/tools/` 配下（tilesets, features, geocoding, stats, analysis, crud）。`stdio`/`sse` 両トランスポート対応。
- **`docker/`** — ローカル PostGIS + Redis（`docker compose`）。スキーマシード SQL は `docker/postgis-init/` に番号順（`04`〜`06`: auth/teams/api_keys、`09`: ローカル開発用 allow-all RLS）。
- **`pg/`** — 本番 DB（Fly Machine 上の PostGIS 単一ノード、`geo-base-pg`）。詳細は `docs/manuals/POSTGRES_SETUP.md`。
- **`packages/shared/`** — 共有パッケージのスケルトン。
- **`scripts/`** — `setup.sh`, `seed_sample_data.{py,fish}`, `fix_bounds.py` 等。

FastAPI は複数環境（ローカル、Fly.io、レガシー Vercel）で動作。`lib/config.py` と `lib/database.py` は `is_vercel` / `is_fly` / `is_serverless` で分岐 — 1つのデプロイモデルだけを前提にしないこと。

## ローカルポート（混同注意）

**現行規約: API=8000、Admin UI=3000**。古いドキュメントに API=3000 と書かれているものは誤り。詳細は `README.md` のポート一覧表を参照。

各コンポーネントのコマンドは各サブディレクトリの README を参照（`api/README.md`、`app/README.md`、`mcp/README.md`）。デプロイは `cd api && fly deploy` / `cd mcp && fly deploy`（Admin UI は push で Vercel が自動デプロイ）。

## 認証モデル

API は自前の **local provider** で認証する（`AUTH_PROVIDER=local` のみサポート）。Supabase Auth は 2026-05-10 に Issue #72 / PR #74 で廃止（プラガブル化の枠組み自体は `api/lib/auth/provider.py` に残存）。

- `local`: 自前の `users` テーブル + JWT 発行（`api/lib/auth/` パッケージ）。初期管理者は `uv run python -m lib.auth.cli create-admin` で作成。
- 認証必須ルート: `Depends(require_auth)`（ユーザー必須）/ `Depends(require_auth_context)`（JWT または API キー）、任意認証: `Depends(get_current_user)` / `Depends(get_auth_context_optional)`。
- タイルセットの `is_public` フラグ: 公開読み取りは認証不要、書き込みは常に認証必須。
- API キー: `lib/routers/api_keys.py` + `lib/auth/api_key_auth.py`。送信ヘッダは `Authorization: Bearer gb_live_...`（`X-API-Key` ではない）。

詳細: `docs/manuals/AUTH_SETUP.md`、E2E チェック: `docs/refs/AUTH_E2E_CHECKLIST.md`。

## 知っておくべき規約

- Python: ruff + black、行長 **100**、ターゲット `py311`。`pytest` は各 `pyproject.toml` で設定済み（`api/` では `addopts = "-v --tb=short"`）。
- Python パッケージマネージャは **`uv` のみ** — `pip` を直接使わないこと。
- シェル例は **fish** 構文（`set -x VAR value`）。CI 用にスクリプト化する場合は bash に変換。
- `pytest` は専用テスト DB（`geo_base_test`）が必須（Issue #47）。`TEST_DATABASE_URL` 未指定だと DB 系テストは fail する。
- ベクタータイルは PostGIS から動的生成（事前焼き込みではない）。動的タイルルーター: `api/lib/routers/tiles/dynamic.py`。キャッシュ: `lib/cache.py`（Redis）+ `lib/tile_cache.py`。
- E2E テスト: shadcn/ui (Radix) の Portal 系コンポーネント（`Select` / `AlertDialog` 等）は `getByRole` selector が headless で間欠 timeout する。新規 E2E は `data-testid` 設計を推奨（詳細: `docs/specs/2026-05-12-radix-portal-playwright-pitfall.md`）。

## ドキュメント

### 言語方針

ドキュメントの種別によって方針が異なる：

- **公開向けドキュメント**（README, デプロイ/セットアップガイド, API リファレンス等）:  
  `.md`（英語）と `.ja.md`（日本語）の**二言語ペア**で作成し、冒頭に相互リンクを入れる。  
  例: `README.md` ↔ `README.ja.md`、`docs/manuals/AUTH_SETUP.md` ↔ `docs/manuals/AUTH_SETUP.ja.md`

- **内部ドキュメント**（HANDOVER, アーキテクチャ判断記録, チェックリスト, `docs/specs/` / `docs/plans/` 等）:  
  **日本語のみ**で作成する（対訳不要）。

コード内の識別子・型注釈・技術用語は英語のままで可。

### 参照先

ドキュメントは `docs/` 配下にサブディレクトリで整理されている:

| ディレクトリ | 用途 | 主なファイル |
|------------|------|------------|
| `docs/handovers/` | 引き継ぎ・完了記録 | `HANDOVER_S3.md`（アクティブ） |
| `docs/plans/` | ロードマップ・実装計画 | `ROADMAP_S3.md`（完了）、`ROADMAP_S4.md`（計画中） |
| `docs/specs/` | 設計仕様・ADR | `2026-05-08-pluggable-auth-design.md` 等 |
| `docs/manuals/` | セットアップ・運用手順書 | `AUTH_SETUP.md`、`POSTGRES_SETUP.md`、`DEPLOY.md` 等 |
| `docs/reports/` | 調査・監査レポート | `ACCESS_CONTROL_REVIEW.md`、`INFRA_MIGRATION_INVESTIGATION.md` 等 |
| `docs/refs/` | チェックリスト・規約 | `AUTH_E2E_CHECKLIST.md`、`I18N_CONVENTIONS.md` 等 |

`geo-base.txt`（約 2.8 MB のダンプ）は無視してオリジナルのソースを読むこと。
