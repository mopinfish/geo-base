# Supabase Auth → local 移行手順

geo-base の認証バックエンドを Supabase Auth から local（自前 JWT 発行）に切り替えるための
オペレーション手順です。Phase 3 / Step 3.3-A で導入されたプラガブル認証を前提とします。

## 前提

- 本番ユーザーは greenfield（既存ユーザーなし、または開発者・社内ユーザー数名のみ）
- Postgres は引き続き Supabase 管理 DB を使用、または別の Postgres プロバイダ
- API は Fly.io（`geo-base-api.fly.dev`）にデプロイ済み
- 切替時にダウンタイム数分を許容できる

> 大量の既存 Supabase ユーザーを抱える環境では、まず Phase 4 で予定している
> マイグレーションスクリプトを待ってください（本ドキュメント末尾参照）。

## 手順

### 1. コード配備（`AUTH_PROVIDER=supabase` のまま）

新しい auth 実装（`lib/auth/` パッケージ、`/api/auth/*` ルーター、`cors_middleware` 等）を含む
リビジョンを Fly.io にデプロイします。`AUTH_PROVIDER` は `supabase` のままにしておくため、
この時点では従来通り Supabase Auth に委譲した挙動になります。

```bash
cd api
fly deploy
```

切替前に動作確認:

```bash
curl https://geo-base-api.fly.dev/api/health
```

### 2. スキーマ追加

`docker/postgis-init/04_auth_schema.sql` を本番 Postgres に適用します。
Supabase 管理 DB の場合は SQL Editor または `psql` 経由で実行可能です:

```bash
psql "$DATABASE_URL" -f docker/postgis-init/04_auth_schema.sql
```

これで以下のテーブルが追加されます（既存の Supabase `auth.users` には触りません）:

- `users`（geo-base 自前のユーザー）
- `refresh_tokens`
- `login_attempts`
- `password_reset_tokens`

### 3. JWT_SECRET と SMTP の設定

```bash
cd api

# JWT_SECRET（local モード必須）
fly secrets set JWT_SECRET="$(openssl rand -base64 64)"

# 本番メール送信（例: SendGrid）
fly secrets set \
  EMAIL_BACKEND=smtp \
  SMTP_HOST=smtp.sendgrid.net \
  SMTP_PORT=587 \
  SMTP_USER=apikey \
  SMTP_PASSWORD=<sendgrid-api-key> \
  SMTP_FROM=no-reply@geo-base.example \
  SMTP_USE_TLS=true \
  INVITATION_BASE_URL=https://geo-base-admin.vercel.app
```

クロスオリジンで Admin UI から refresh Cookie を扱うため、Cookie ポリシーも調整します:

```bash
fly secrets set COOKIE_SAMESITE=none COOKIE_SECURE=true
```

`CORS_ORIGINS` は本番 Admin UI を含むよう更新してください:

```bash
fly secrets set CORS_ORIGINS=https://geo-base-admin.vercel.app
```

### 4. 初期管理者作成

本番 API コンテナに入り、CLI で最初の管理者ユーザーを作成します:

```bash
fly ssh console -C "cd /app && uv run python -m lib.auth.cli create-admin --email <admin-email>"
```

対話的にパスワードを入力します。`getpass` が SSH 越しで動作しない環境では、ローカルから
`DATABASE_URL` を本番 DB に向けて `python -m lib.auth.cli create-admin` を実行する手もあります
（その場合は実行マシンの IP が DB アクセス許可されていることを確認）。

### 5. `AUTH_PROVIDER` の切り替え

```bash
fly secrets set AUTH_PROVIDER=local
```

`fly secrets set` は API を自動再起動します。再起動が完了すれば local プロバイダで稼働開始です。

### 6. 動作確認

```bash
# ヘルスチェック
curl https://geo-base-api.fly.dev/api/health

# Admin UI (https://geo-base-admin.vercel.app) で先ほど作った管理者でログイン
# - /login → email + password 入力
# - ダッシュボードが表示されればログイン成功
# - /settings/profile, /settings/password で各種更新を試す
```

API キーで保護されたエンドポイントも、JWT 認証フローと並行して引き続き動作します。

### ロールバック

問題が発覚した場合は即座に元に戻せます:

```bash
fly secrets set AUTH_PROVIDER=supabase
```

local モードで作成した `users` / `refresh_tokens` 等のテーブルは残りますが、
Supabase Auth 経由の認証パスには干渉しないため放置で問題ありません。

DB スキーマを完全にクリーンアップしたい場合は手動で `DROP TABLE` できますが、
再度切替を試す可能性があるなら残しておくことを推奨します。

## 既存 Supabase ユーザーがいる場合

設計書 §1.3 の通り、Phase 3 では Supabase Auth から local への **ユーザー移行スクリプトは
提供しません**。既存ユーザーをそのまま引き継ぎたいケースは Phase 4 のスコープです。

暫定対応:

- 既存 Supabase ユーザーには「再度サインアップしてください」と案内し、`accept-invitation`
  または `password-reset/request` 経由で local の `users` テーブルにレコードを生成してもらう
- もしくは現状の Supabase モード継続でしばらく運用し、Phase 4 のマイグレーションを待つ

## 関連ドキュメント

- セットアップガイド: `docs/AUTH_SETUP.md`
- 設計書: `docs/superpowers/specs/2026-05-08-pluggable-auth-design.md`
- 実装計画: `docs/superpowers/plans/2026-05-08-pluggable-auth.md`
