# geo-base デプロイガイド

> [!NOTE]
> 本ドキュメントは **デプロイ全体像のサマリ** です。各コンポーネントの詳細手順は
> 該当ドキュメントを参照してください。
>
> 旧 Vercel API デプロイ手順 (Vercel + Supabase 構成) は 2026-05-10 までに廃止済みで、
> 過去版は git history から参照できます。

## 現行アーキテクチャ

| コンポーネント | プラットフォーム | URL | デプロイ手順 |
|---|---|---|---|
| API (FastAPI) | Fly.io | `geo-base-api.fly.dev` | [`api/FLY_DEPLOY.md`](./api/FLY_DEPLOY.md) |
| MCP Server | Fly.io | `geo-base-mcp.fly.dev` | `cd mcp && fly deploy` |
| Admin UI (Next.js) | Vercel | `geo-base-admin.vercel.app` | GitHub push で auto-deploy |
| PostgreSQL + PostGIS | Fly.io (`geo-base-pg`) | internal: `geo-base-pg.flycast` | [`docs/POSTGRES_SETUP.md`](./docs/POSTGRES_SETUP.md) |
| Redis | Upstash (キャッシュ) | — | env `REDIS_URL` 経由 |
| Storage (COG/PMTiles) | Fly Tigris (S3 互換) | — | Issue #72 Phase 1.2 で切替予定 |

## ブランチと自動化

- **`develop`**: アクティブな開発ブランチ。各 PR は develop に向けてマージ
- **`main`**: 安定リリース用（Vercel Production が main をトラッキング）
- API/MCP の本番反映は **手動 `fly deploy`**（auto-deploy は未設定）
- Admin UI の本番反映は **main への push で Vercel が自動デプロイ**

## 認証

- `AUTH_PROVIDER=local` のみサポート（`docs/AUTH_SETUP.md`）
- 初期管理者作成: `flyctl ssh console -a geo-base-api -C 'python -m lib.auth.cli create-admin --email <email>'`

## トラブルシューティング

DB 接続不調 / API 起動失敗等は各コンポーネントガイドの「トラブルシューティング」セクションを参照:

- API 側: [`api/FLY_DEPLOY.md`](./api/FLY_DEPLOY.md)
- DB 側: [`docs/POSTGRES_SETUP.md`](./docs/POSTGRES_SETUP.md) §4
- 認証: [`docs/AUTH_SETUP.md`](./docs/AUTH_SETUP.md) のトラブルシューティング

## 関連ドキュメント

- アーキテクチャ判断記録: [`docs/INFRA_MIGRATION_INVESTIGATION.md`](./docs/INFRA_MIGRATION_INVESTIGATION.md)
- 認可レビュー: [`docs/ACCESS_CONTROL_REVIEW.md`](./docs/ACCESS_CONTROL_REVIEW.md)
- ローカル開発: [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md)
