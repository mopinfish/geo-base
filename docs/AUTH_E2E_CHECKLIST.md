# 認証 E2E 手動テストチェックリスト

Phase 3 / Step 3.3-A（プラガブル認証）のリリース前に手動で実施するテスト手順。

自動テスト（`uv run pytest tests/`）とは別レイヤで、ブラウザ越しの実フローを検証する。

関連ドキュメント:

- `docs/AUTH_SETUP.md` — local モードのセットアップ詳細
- `docs/AUTH_MIGRATION.md` — supabase → local 切替手順
- `docs/superpowers/plans/2026-05-08-pluggable-auth.md` — 元の実装計画（Task 8.2 / 8.3）

---

## テスト DB（geo_base_test）

issue #47 の対応で、**pytest は専用のテスト DB に接続するように分離されました**。`conftest.py` のフィクスチャは `TEST_DATABASE_URL` を必須とし、未設定 or `DATABASE_URL` と同一の場合は `pytest.fail` で停止します。これにより、E2E 中に `pytest tests/` を流しても dev DB（`geo_base`）は破壊されません。

### セットアップ

`docker compose up -d` 初回起動時、`docker/postgis-init/99_create_test_db.sh` が `geo_base_test` を自動作成しスキーマを clone します。

既存の volume を維持したまま手動で作る場合:

```bash
docker compose exec postgis psql -U postgres -c "CREATE DATABASE geo_base_test;"
docker compose exec postgis bash -c \
  'pg_dump -U postgres --schema-only --no-owner --no-acl geo_base | psql -U postgres -d geo_base_test'
```

### 実行

```bash
cd api
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base_test
uv run pytest tests/ -q
```

`api/.env.example` にも `TEST_DATABASE_URL` のサンプルを追加してあります。CI を導入する際は CI 環境で必ず `TEST_DATABASE_URL` をセットしてください（dev DB と同一値だと `pytest.fail` で落ちます）。

## 注意: テストアカウントの email

`*.test` / `*.localhost` / `*.invalid` などの **RFC 2606 で予約された TLD** は API の `EmailStr` バリデーションに弾かれます（`email-validator` パッケージの仕様）。

テスト用には以下のように **実在する TLD** を使ってください:
- ✅ `admin@example.com`、`admin@example.org`（RFC 2606 で documentation 用に予約された **第 2 階層**ドメイン、TLD は `.com` / `.org`）
- ✅ `admin@geo-base.dev` 等の自前ドメイン
- ❌ `admin@local.test`、`admin@example.test`、`admin@foo.localhost`

## 前提条件

- Docker Desktop 起動済み
- ポート 3000 / 8000 / 15432（または 5432）/ 6379 が空いている
- リポジトリのブランチ: `feat/s3_3-3_team_and_role`（または merge 後の `main`）
- API / Admin UI の依存はインストール済み（`uv sync --extra dev`、`npm install`）

ホスト Postgres ポートに注意: 別プロジェクトが 5432 を占有している場合、`geo-base-postgis` は **15432** で動作する（HANDOVER_S3.md 参照）。

---

## Part A: local モード E2E

### A-1. クリーン起動

```bash
# 1. PostGIS / Redis をクリーン状態で起動
cd docker
docker compose down -v
docker compose up -d
sleep 10

# 2. API .env 作成（DATABASE_URL は環境に合わせて 5432 / 15432 を選ぶ）
cd ../api
cat > .env <<EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base
AUTH_PROVIDER=local
JWT_SECRET=$(openssl rand -base64 64)
EMAIL_BACKEND=console
INVITATION_BASE_URL=http://localhost:3000
CORS_ORIGINS=["http://localhost:3000"]
EOF

# 3. 初期管理者を作成（パスワード対話入力: 例 TestPass123）
uv run python -m lib.auth.cli create-admin --email admin@example.com
```

### A-2. サーバ起動

別ターミナルでそれぞれ起動:

```bash
# Terminal 1: API
cd api
uv run uvicorn lib.main:app --reload --port 8000

# Terminal 2: Admin UI
cd app
npm run dev
```

ブラウザで <http://localhost:3000> にアクセス。

### A-3. チェック項目

- [ ] **A-3-1 ログイン**: `/login` で `admin@example.com` / `TestPass123` でログイン成功 → `/` にリダイレクト
- [ ] **A-3-2 認証保護ルート表示**: `/tilesets` が表示される（未ログインだと `/login?next=/tilesets` にリダイレクトされる）
- [ ] **A-3-3 プロフィール更新**: `/settings/profile` で名前を変更 → 「更新しました」表示 → 再読込しても新しい名前が表示
- [ ] **A-3-4 パスワード変更**: `/settings/password` で現在 / 新パスワードを入力 → 成功時に **自動ログアウトされて `/login?password_changed=1` へ遷移**
- [ ] **A-3-5 旧パスワードでログイン失敗 → 新で成功**: A-3-4 直後に旧パスワードでログイン失敗、新パスワードで成功することを確認
- [ ] **A-3-6 チーム作成 + 招待発行**: 適当なチームを作成 → メンバー招待 (`invitee@example.com` 等) を発行 → **API ターミナルに招待メール内容（リンク含む）が `console` バックエンドで出力される** ことを確認
- [ ] **A-3-7 招待受諾フロー**: 招待リンクをコピー → 別ブラウザ（プライベートウィンドウ可）で開く → `/accept-invitation?token=...` 画面 → サインアップ（パスワード設定） → 自動ログイン → チームメンバーに追加されている
- [ ] **A-3-8 パスワードリセット要求**: `/password-reset/request` でメールアドレス入力 → 送信後の確認画面表示 → API ターミナルにリセットリンクが出力される
- [ ] **A-3-9 パスワードリセット完了**: リセットリンク経由で `/password-reset/confirm?token=...` → 新パスワード設定 → `/login?reset=success` にリダイレクト → 旧パスワードでログイン失敗、新パスワードで成功

### A-4. 後始末

```bash
# サーバ停止後
cd docker && docker compose down -v
```

`api/.env` は実環境ごとに上書きされる前提のため、コミット対象外（`.gitignore` 済み）。

---

## Part B: supabase モード E2E

> 既存の Supabase テストプロジェクトと、それに登録済みのテストユーザーが必要。

### B-1. 設定切替

`api/.env` を以下に変更（既存の local モード設定をコメントアウトまたは削除）:

```bash
AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-test-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<test-service-role-key>
SUPABASE_JWT_SECRET=<test-jwt-secret>
DATABASE_URL=postgresql://...   # 必要に応じてテスト Supabase の DB URL に
CORS_ORIGINS=["http://localhost:3000"]
```

API を再起動（uvicorn を Ctrl-C → 再実行）。

### B-2. チェック項目

- [ ] **B-2-1 Supabase ユーザーでログイン**: Supabase Dashboard で事前作成したテストユーザー（email + password）で `/login` から成功
- [ ] **B-2-2 タイル一覧表示**: `/tilesets` が表示される（過去データの ownership は Supabase の `auth.uid()` 紐付けに依存）
- [ ] **B-2-3 チーム表示**: 既存チームが表示される
- [ ] **B-2-4 ログアウト**: サイドバーのログアウトで `/login` に戻る → 再度認証ガードが効く

> Supabase モードでの新規招待 / パスワードリセットの完全フローは Supabase Auth の仕様に依存するため、`SupabaseAuthProvider` の対応範囲（spec §1.3）に応じて検証範囲を判断する。

### B-3. 後始末

```bash
# .env を local モードに戻すか、テスト用の値を削除
```

---

## Part C: 統合観点（横断チェック）

local / supabase 両モードで共通に確認したい横断項目:

- [ ] **C-1 401 自動 refresh**: ログイン後、ブラウザ DevTools で `geo_base_access` cookie を削除して再リクエスト → `/api/auth/refresh` 経由で自動的に新アクセストークン取得 → 元のリクエストが retry されて成功
- [ ] **C-2 CORS**: `/api/auth/*` は strict（`CORS_ORIGINS` 一致のみ）、`/api/tiles/*` は寛容（ワイルドカード）の挙動
- [ ] **C-3 middleware route guard**: 未ログインで `/tilesets` にアクセス → `/login?next=/tilesets` に redirect / ログイン後 `/login` にアクセス → `/` に redirect
- [ ] **C-4 ビルド成功**: `cd app && npm run build` がエラーなく成功
- [ ] **C-5 全テスト PASS**: `cd api && DATABASE_URL=... uv run pytest tests/ --tb=short -q`

---

## トラブルシューティング

| 症状 | 原因 / 対処 |
|---|---|
| `/api/auth/refresh` で 401 | `geo_base_refresh` cookie が未送信 → Admin UI と API のオリジン違いで `credentials: include` が効いていない可能性。`next.config.ts` の dev rewrites か `NEXT_PUBLIC_API_URL` を確認 |
| 招待メール / リセットメールが出ない | `EMAIL_BACKEND=console` が API .env に入っていない。SMTP モードなら `SMTP_*` 環境変数を確認 |
| ログインで「ロックされました」 | 同一 IP/email から短時間に 5 回失敗 → 15 分待つか、Postgres から `auth_login_attempts` テーブルをクリア |
| `npm run dev` で `@supabase/*` の import エラー | Phase 6 で削除した残骸。`grep -rn "@supabase" app/src/` を実行して洗い出し |
| Docker compose 起動で port conflict | 既に別プロジェクトが 5432 を占有 → `docker/docker-compose.override.yml` 等で 15432 に変更（HANDOVER_S3.md 参照） |

---

## 改訂履歴

| 日付 | 変更内容 |
|---|---|
| 2026-05-08 | 初版作成（Phase 3 / Step 3.3-A 完了に伴う E2E 手順を計画書から独立ファイル化） |
| 2026-05-10 | issue #47: テスト DB 分離（`TEST_DATABASE_URL` 必須化）に伴い「pytest との DB 共有に注意」セクションを「テスト DB（geo_base_test）」に置き換え |
