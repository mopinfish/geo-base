# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ構成

`geo-base` は地理空間タイルサーバーシステムのモノレポ。3コンポーネントが1つの PostGIS DB を共有する。

| コンポーネント | 技術 | デプロイ先 |
|---|---|---|
| `api/` | FastAPI + uv（ベクター/ラスタータイル、認証、APIキー） | Fly.io `geo-base-api.fly.dev` |
| `app/` | Next.js 16 + React 19 + Tailwind v4 + shadcn/ui | Vercel `geo-base-admin.vercel.app` |
| `mcp/` | FastMCP（24+ ツール、stdio/sse） | Fly.io `geo-base-mcp.fly.dev` |
| `docker/` | ローカル PostGIS + Redis（`docker compose`） | ローカル開発のみ |

- `docker/postgis-init/` の SQL は番号順に実行（`04`〜`06`: auth/teams/api_keys、`09`: allow-all RLS）
- `lib/config.py` / `lib/database.py` は `is_fly` / `is_serverless` で環境分岐 — 単一環境を前提にしないこと
- **ローカルポート: API=8000、Admin UI=3000**（古いドキュメントの API=3000 は誤り）

## 認証モデル

`AUTH_PROVIDER=local` のみサポート（Supabase Auth は PR #74 で廃止済み）。

- 初期管理者作成: `uv run python -m lib.auth.cli create-admin`
- `is_public=true` のタイルセットは読み取り認証不要、書き込みは常に必須
- APIキー送信ヘッダ: `Authorization: Bearer gb_live_...`（`X-API-Key` ではない）
- 詳細: `docs/manuals/AUTH_SETUP.md` / E2E チェック: `docs/refs/AUTH_E2E_CHECKLIST.md`

## 知っておくべき規約

- Python パッケージマネージャは **`uv` のみ**（`pip` 直接使用禁止）
- シェル例は **fish** 構文（`set -x VAR value`）。CI スクリプト化は bash に変換
- `pytest` は専用 DB 必須: `TEST_DATABASE_URL=postgresql://...@localhost:15432/geo_base_test`
- E2E テスト: Radix Portal 系（`Select` / `AlertDialog`）は `getByRole` が headless で間欠 timeout → **`data-testid` 設計を推奨**（詳細: `docs/specs/2026-05-12-radix-portal-playwright-pitfall.md`）

## ドキュメント

### 言語方針

- **公開向け**（README, セットアップガイド等）: `.md`（英語）+ `.ja.md`（日本語）の二言語ペア
- **内部向け**（HANDOVER, specs, plans, チェックリスト等）: 日本語のみ

### docs/ 構造

| ディレクトリ | 用途 |
|---|---|
| `docs/handovers/` | 引き継ぎ・完了記録（`HANDOVER_S3.md` がアクティブ） |
| `docs/plans/` | ロードマップ・実装計画（`ROADMAP_S4.md` が最新） |
| `docs/specs/` | 設計仕様・ADR・落とし穴メモ |
| `docs/manuals/` | セットアップ・運用手順書 |
| `docs/reports/` | 調査・監査レポート |
| `docs/refs/` | チェックリスト・規約 |

`geo-base.txt`（約 2.8 MB のダンプ）は無視してオリジナルのソースを読むこと。
