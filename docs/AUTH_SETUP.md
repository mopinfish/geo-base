# 認証セットアップガイド

geo-base API は自前の **local provider** で認証する（`AUTH_PROVIDER=local`）。
プラガブル化の枠組み (`api/lib/auth/provider.py`) 自体は将来別 IdP を追加できるように
残してあるが、**現状サポートされるのは `local` のみ**。

> 過去には `AUTH_PROVIDER=supabase` で Supabase Auth に委譲する構成も
> サポートしていたが、本番 DB を Fly Postgres に移行 (PR #73) し Supabase Auth
> プロバイダ実装も削除 (PR #74 / Issue #72) したため、2026-05-10 以降は廃止。
> Supabase からの移行記録は `docs/AUTH_MIGRATION.md` を参照（履歴文書）。

設計の背景・全体像は `docs/superpowers/specs/2026-05-08-pluggable-auth-design.md` を参照。
本ドキュメントは **ローカル / 本番の構築手順** に絞ったハンズオンです。

関連: リリース前の手動 E2E チェックは `docs/AUTH_E2E_CHECKLIST.md`、認可仕様の網羅レビューは `docs/ACCESS_CONTROL_REVIEW.md`、本番 DB 構築は `docs/POSTGRES_SETUP.md`。

---

## クイックスタート（local モード）

ローカル開発で local プロバイダを動かす最短手順。

### 1. PostGIS 起動

```bash
cd docker
docker compose up -d postgis
```

`docker/postgis-init/04_auth_schema.sql` が初期化時に適用され、`users` / `refresh_tokens` /
`login_attempts` / `password_reset_tokens` テーブルが作成されます。

### 2. 環境変数

`api/.env` を作成（`api/.env.example` は最新の変数リストを反映済み）:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base

# 認証プロバイダ
AUTH_PROVIDER=local
JWT_SECRET=$(openssl rand -base64 64)   # 必須。実際の値を貼り付ける
JWT_AUDIENCE=authenticated
JWT_ISSUER=geo-base
ACCESS_TOKEN_TTL_SECONDS=900

# メール送信（local モードの招待・パスワードリセット用）
EMAIL_BACKEND=console                     # 開発時はコンソール出力で十分
INVITATION_BASE_URL=http://localhost:3000

# CORS / Cookie
CORS_ORIGINS=http://localhost:3000
COOKIE_SAMESITE=lax
COOKIE_SECURE=false

# 任意: signup を許可するかどうか（招待フローのみ運用するなら false）
LOCAL_AUTH_ALLOW_SIGNUP=false
```

> `JWT_SECRET` は必ず `openssl rand -base64 64` 等で **64 バイト以上** をランダム生成してください。
> 設定漏れがあると API 起動時に `Settings` バリデーションで失敗します（`AUTH_PROVIDER=local requires JWT_SECRET ...`）。

### 3. 初期管理者作成

API サーバーを起動する前に、CLI で最初の管理者ユーザーを作ります:

```bash
cd api
uv sync
uv run python -m lib.auth.cli create-admin --email admin@example.com
# Password: ********
# Confirm password: ********
# Name (optional): Admin
# OK Admin user created: <uuid>
```

### 4. API 起動

```bash
cd api
uv run uvicorn lib.main:app --reload --port 8000
```

ヘルスチェック:

```bash
curl http://localhost:8000/api/health
```

### 5. Admin UI 起動

別ターミナルで:

```bash
cd app
npm install
npm run dev
```

ブラウザで http://localhost:3000/login にアクセスし、先ほど作成した
`admin@example.com` のメール/パスワードでログイン。

---

## 主要な API エンドポイント

`api/lib/routers/auth.py` 配下に集約されています。Origin チェック付きの state-changing
エンドポイントは Refresh Cookie + Bearer access_token の併用が前提です。

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| POST | `/api/auth/login` | – | email + password でログイン。`access_token` を返却し、`geo_base_refresh` Cookie を設定 |
| POST | `/api/auth/refresh` | Refresh Cookie | access_token を再発行。Cookie をローテーション |
| POST | `/api/auth/logout` | Refresh Cookie | refresh token を失効、Cookie 削除 |
| GET | `/api/auth/me` | Bearer | 現在のユーザー情報 |
| PATCH | `/api/auth/me` | Bearer | name / email / metadata 更新 |
| POST | `/api/auth/me/password` | Bearer | パスワード変更（要・現パスワード） |
| POST | `/api/auth/password-reset/request` | – | パスワードリセットメール送信（情報漏洩防止のため常に 204） |
| POST | `/api/auth/password-reset/confirm` | – | リセットトークンで新パスワードを設定 |
| GET | `/api/auth/invitations/{token}` | – | 招待メタ情報を取得（受諾画面用） |
| POST | `/api/auth/accept-invitation` | – | 招待を受諾し新規ユーザー作成 + 自動ログイン |

ベース URL はローカルでは `http://localhost:8000`、本番は `https://geo-base-api.fly.dev` を使ってください。

---

## API キーで書き込み操作を行う（issue #50）

外部システム連携（CI からのタイルアップロード、自動データ同期、エージェント経由の更新等）には JWT ではなく **API キー** を使うことを推奨します。

### スコープと操作の対応

| 必要 scope | 対象操作 |
|---|---|
| `read` | GET 系（feature 取得、tileset 詳細、datasource 取得 等） |
| `write` | POST/PATCH 系（tileset / feature / datasource の作成・更新） |
| `delete` | DELETE 系（tileset / feature / datasource の削除） |

`write` は `read` を、`delete` は `write` を、`admin` はすべてを包含します（[AuthContext.has_scope()](../api/lib/auth/context.py) の階層）。

### API キーの作成

**Admin UI**: ログイン後 `/api-keys` ページから作成（推奨、ブラウザのみで完結）。

**API エンドポイント直叩き**: 既存の JWT で `POST /api/api-keys` を呼び出す:

```bash
curl -X POST https://geo-base-api.fly.dev/api/api-keys \
  -H "Authorization: Bearer $JWT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ci-uploader",
    "scopes": ["read", "write"],
    "team_id": null
  }'
```

返却された `gb_live_xxx...` 形式のトークンを **発行時にしか取得できない**（DB には hash のみ保管）ので保管してください。

実装は `api/lib/routers/api_keys.py:create_api_key` 参照。

### 書き込みリクエスト例

#### 個人タイルセットを更新する（`scope=write`）

```bash
curl -X PATCH https://geo-base-api.fly.dev/api/tilesets/$TILESET_ID \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "更新後の名前"}'
```

#### チーム共有タイルセットを更新する（`scope=write` + team API キー）

API キー作成時に `team_id` を指定（Admin UI のチーム選択 / API リクエスト body の `"team_id"`）し、対象タイルセットがそのチームに `team_tilesets.permission_level >= write` で共有されている必要があります。

```bash
curl -X PATCH https://geo-base-api.fly.dev/api/tilesets/$SHARED_TILESET_ID \
  -H "Authorization: Bearer $TEAM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "team-update"}'
```

#### 削除する（`scope=delete`）

```bash
curl -X DELETE https://geo-base-api.fly.dev/api/tilesets/$TILESET_ID \
  -H "Authorization: Bearer $DELETE_API_KEY"
```

チーム共有タイルセットを削除するには `team_tilesets.permission_level='admin'` が必要です（`write` では 403）。

### 認可のレイヤー

書き込みは 2 段階で判定されます:

1. **Scope ガード**: API キーが必要な scope を持つか（`write` / `delete`）
2. **リソース認可**: 対象タイルセットへの書き込み権限があるか
   - 個人タイルセット所有者 → 常に可
   - team API キー（`team_id` セット）→ `team_tilesets.permission_level` を判定（API キーは team_role の継承を行わない）

詳細は [`docs/ACCESS_CONTROL_REVIEW.md`](./ACCESS_CONTROL_REVIEW.md) §C-2 と [issue #50](https://github.com/mopinfish/geo-base/issues/50) を参照。

### よくあるエラー

| HTTP | 典型的な detail | 原因 / 対処 |
|---|---|---|
| 401 | `Authentication required` 等 | `Authorization: Bearer <api_key>` 形式を確認 |
| 403 | `write scope required to create tileset`（POST /api/tilesets のみ専用メッセージ）/ `Not authorized to ...`（その他の write 系。scope 不足とリソース認可不足を区別せず単一メッセージで返す） | scope 不足: 必要な `scopes`（`write` / `delete`）を含めて API キーを再発行。リソース認可: team API キーの場合は `team_id` と `team_tilesets.permission_level` を確認 |
| 429 | `API key rate limit exceeded` | rate limit 超過。後述の rate limit セクションを参照 |

---

## 環境変数リファレンス

詳細仕様（バリデーションルール含む）は設計書 §9.1 を参照。ここでは主要変数のみ列挙します。

### 認証プロバイダ

| 変数 | デフォルト | 説明 |
|---|---|---|
| `AUTH_PROVIDER` | `local` | `local` のみサポート（Supabase 等に拡張する余地は残してある） |
| `JWT_SECRET` | – | 必須。64 バイト以上を `openssl rand -base64 64` 等で生成 |
| `JWT_AUDIENCE` | `authenticated` | JWT `aud` クレーム |
| `JWT_ISSUER` | `geo-base` | JWT `iss` クレーム |
| `ACCESS_TOKEN_TTL_SECONDS` | `900` | access_token の有効期限（秒） |

### メール

| 変数 | デフォルト | 説明 |
|---|---|---|
| `EMAIL_BACKEND` | `console` | `null` / `console` / `smtp` |
| `INVITATION_BASE_URL` | `http://localhost:3000` | 招待 / リセットリンクの base URL（Admin UI の origin） |
| `SMTP_HOST` | – | `EMAIL_BACKEND=smtp` 必須 |
| `SMTP_PORT` | `587` | – |
| `SMTP_USER` | – | – |
| `SMTP_PASSWORD` | – | – |
| `SMTP_FROM` | – | `EMAIL_BACKEND=smtp` 必須 |
| `SMTP_USE_TLS` | `true` | – |

### CORS / Cookie

| 変数 | デフォルト | 説明 |
|---|---|---|
| `CORS_ORIGINS` | `["*"]` | カンマ区切り or JSON 配列。Admin UI の origin を含めること |
| `COOKIE_SAMESITE` | `lax` | `lax` / `strict` / `none`。クロスオリジンで refresh する場合は `none` |
| `COOKIE_SECURE` | `false` | `true` で HTTPS 限定。`COOKIE_SAMESITE=none` の場合は必須 |
| `COOKIE_DOMAIN` | – | 通常は未設定で OK |

### local プロバイダ固有

| 変数 | デフォルト | 説明 |
|---|---|---|
| `LOCAL_AUTH_ALLOW_SIGNUP` | `false` | パブリック signup を許可するかどうか。招待フロー中心の運用なら `false` |

---

## 運用 CLI

`uv run python -m lib.auth.cli <subcommand>`（カレントは `api/` ディレクトリ）。

| サブコマンド | 用途 |
|---|---|
| `create-admin --email <email>` | 初期管理者ユーザー作成（`role=admin`、`email_verified=true`） |
| `revoke-user-tokens <user_id>` | 指定ユーザーの refresh_token をすべて失効 |
| `cleanup-expired` | 失効済みの refresh_token / login_attempts / password_reset_tokens / 期限切れ招待を削除 |
| `reset-password --email <email>` | パスワードリセットメールを送信 |
| `list-users [--json]` | 登録ユーザー一覧 |

### `cleanup-expired` の定期実行

`refresh_tokens` / `login_attempts` / `password_reset_tokens` / `team_invitations` テーブルが
期限切れレコードで肥大化するのを防ぐため、`cleanup-expired` を **1 日 1 回**実行します。

#### GitHub Actions による自動実行（運用）

`.github/workflows/cleanup-expired.yml` に定義済み。Fly.io 上で本番イメージをそのまま再利用した
`--rm` 一時マシンを起動して CLI を実行する方式です。

| 項目 | 値 |
|---|---|
| スケジュール | 毎日 18:00 UTC（= 03:00 JST） |
| ワークフロー名 | `Cleanup expired tokens` |
| 必要な Secret | `FLY_API_TOKEN`（GitHub repo Settings → Secrets and variables → Actions） |

**初期セットアップ:**

1. Fly.io API トークンを取得:
   ```bash
   flyctl auth token
   ```
2. GitHub リポジトリで `Settings` → `Secrets and variables` → `Actions` → `New repository secret` を開き、
   `FLY_API_TOKEN` という名前で貼り付ける。
3. ワークフローは push 後の最初の 18:00 UTC から自動実行されます。

**手動実行（即時クリーンアップしたい場合）:**

GitHub の `Actions` タブ → `Cleanup expired tokens` → `Run workflow` ボタンで起動できます。

**ローカル実行（開発時）:**

```bash
cd api && uv run python -m lib.auth.cli cleanup-expired
```

**失敗時のアラート:**

GitHub Actions のデフォルト通知（リポジトリ Watcher / 失敗通知設定）に依存します。
Slack / Sentry 連携は別途検討（将来的な改善余地）。

---

## トラブルシューティング

### `AUTH_PROVIDER=local requires JWT_SECRET ...` で起動失敗

`JWT_SECRET` 未設定。`openssl rand -base64 64` で生成して `api/.env` に貼り付けてください。
（以前は `SUPABASE_JWT_SECRET` フォールバックがあったが PR #74 で削除済み。）

### CORS エラー（ブラウザコンソールに `blocked by CORS policy`）

`CORS_ORIGINS` に Admin UI の origin（例: `http://localhost:3000`）が含まれていません。
カンマ区切り文字列または JSON 配列で複数指定可能です:

```bash
CORS_ORIGINS=http://localhost:3000,https://geo-base-admin.vercel.app
```

### refresh が 403 `Origin not allowed` で失敗

`/api/auth/refresh` `/logout` `/login` 等の state-changing エンドポイントは
リクエスト `Origin` ヘッダを `CORS_ORIGINS` と照合します。Admin UI の origin が許可リストに
入っているか確認してください。

### メールが届かない（local モード）

- `EMAIL_BACKEND=console`: 送信内容は API のログに **コンソール出力** されます（実際のメールは飛びません）。
  招待 URL やリセットトークンはログから拾ってください。
- `EMAIL_BACKEND=smtp`: `SMTP_HOST` / `SMTP_FROM` 等が未設定だと起動時にバリデーション失敗します。
  SendGrid / Mailgun 等のクレデンシャルを `fly secrets` で設定してください。

### ログインがロックされる（429 Too Many Requests）

同一 IP / email から短期間に連続失敗すると `login_attempts` テーブルでカウントされ、
レート制限が発動します（既定: 5 回失敗で 15 分ロック）。`uv run python -m lib.auth.cli cleanup-expired`
または該当行を直接削除すれば解除できます。

---

## 関連ドキュメント

- Supabase からの移行履歴: `docs/AUTH_MIGRATION.md`（完了済み）
- 設計書: `docs/superpowers/specs/2026-05-08-pluggable-auth-design.md`（履歴）
- 実装計画: `docs/superpowers/plans/2026-05-08-pluggable-auth.md`（履歴）
- ローカル開発全般: `LOCAL_DEVELOPMENT.md`
