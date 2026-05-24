# プラガブル認証・認可（RBAC）設計仕様

| 項目 | 内容 |
|---|---|
| **ステータス** | 設計承認済み（実装計画作成待ち） |
| **作成日** | 2026-05-08 |
| **対象ブランチ** | `feat/s3_3-3_team_and_role` |
| **関連 Phase** | Season 3 / Phase 3 / Step 3.3-A 拡張 |
| **関連ドキュメント** | `docs/INFRA_MIGRATION_INVESTIGATION.md`（前提となるインフラ移行検討） |

---

## 1. 目的とゴール

### 1.1 背景

`docs/INFRA_MIGRATION_INVESTIGATION.md` で Cloudflare 一本化移行を検討した結果、**現状インフラ（Vercel + Fly.io + Supabase）を当面維持**する方針を決定した。ただし将来の移行可能性を残すため、**Supabase 依存を極力薄くする**設計をチーム/ロールベース認可システム（Phase 3 / Step 3.3-A）で採用する。

### 1.2 ゴール

1. **プラガブル認証バックエンド**: 起動時に環境変数で認証プロバイダを切替（local / supabase の 2 実装、将来 Better Auth 等を追加可能）
2. **ローカル PostgreSQL+PostGIS のみで完結**: Supabase 不要で同等機能が動作
3. **既存の team/role / API キーコードは温存**: 既に portable に書かれているため、認証層の差し替えだけで素の Postgres 対応
4. **Admin UI も Supabase 抜きで動作**: `@supabase/ssr` を撤去、自前認証クライアントに置換
5. **チーム/ロールベース認可**: タイル API 等のリソースに対するロール別アクセス制御（既存 `team_members.role` ＋ `team_tilesets.permission_level`）
6. **API キーによる第三者・ヘッドレスアクセス**: タイル API は CORS 公開・API キーで行レベル認可

### 1.3 非ゴール（Phase 4 以降）

- MFA（TOTP）
- OAuth ソーシャルログイン（Google/GitHub 等）
- アカウント無効化・復活
- ログイン履歴の監査ログ UI
- 複数デバイスのセッション管理 UI
- HTML メール（Phase 3 はプレーンテキストのみ）
- Have I Been Pwned 等のパスワードブラックリスト
- フロントエンド E2E テスト（Playwright 等）
- 既存 Supabase ユーザーデータの移行スクリプト（greenfield 想定）

---

## 2. 設計判断サマリー

| 項目 | 決定 |
|---|---|
| ユーザー作成ポリシー | **招待制のみ**（公開サインアップなし、初期 admin は CLI で発行） |
| 既存ユーザー移行 | **不要**（greenfield 同等、移行スクリプトなし） |
| ローカルプロバイダ機能スコープ | Email/Password、リフレッシュトークン、パスワードリセット、メール検証、CLI ブートストラップ、プロフィール変更、レート制限 |
| メール送信バックエンド | **Null / Console / SMTP** のプラガブル（標準 SMTP プロトコル、外部 SDK 不要） |
| RLS 戦略 | Phase 3 はローカル permissive（アプリ層認可）、Phase 4 でポータブル RLS（`current_setting('app.user_id')` 方式） |
| Admin UI | **Supabase 撤去**、自前 AuthClient で置換 |
| 既存ブランチ作業 | 温存し、差分で Supabase 非依存化 |
| 抽象化粒度 | **単一 AuthProvider インタフェース + 共有ユーティリティ**（粗すぎず細かすぎず） |
| JWT 署名アルゴリズム | HS256（共有秘密鍵） |
| パスワードハッシュ | bcrypt cost=12（`passlib[bcrypt]`） |
| アクセストークン TTL | 15 分 |
| リフレッシュトークン TTL | 30 日（DB 保存・revoke 可能、rotation 採用） |
| プロバイダ切替 | 環境変数 `AUTH_PROVIDER=local\|supabase`（同時稼働なし） |
| Admin UI セッション | アクセストークンはメモリ、リフレッシュは HttpOnly Cookie（SameSite=Lax / 本番 None） |
| ログイン失敗レート制限 | 同一 email/IP で 5 回失敗 / 15 分 → 429 |
| タイル API CORS | **公開（`*`）**、API キーまたは JWT で行レベル認可 |

---

## 3. アーキテクチャ全体像

### 3.1 コンポーネント図

```
┌──────────────────────────────────────────────────────────────────┐
│                       Admin UI (Next.js)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │ Login Page  │  │ Signup       │  │ AuthClient            │   │
│  │ /login      │  │ (招待受諾    │  │ (app/src/lib/auth/)   │   │
│  │             │  │  /signup     │  │ - login(email, pw)    │   │
│  │             │  │  /accept-    │  │ - logout()            │   │
│  │             │  │  invitation) │  │ - refresh()           │   │
│  └─────────────┘  └──────────────┘  │ - getAccessToken()    │   │
│                                     └────────────┬──────────┘   │
│                                                  │              │
│                            HttpOnly Cookie       │              │
│                            (refresh_token)       │              │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI (api/lib/)                          │
│                                                                   │
│  ┌──────────────────── TwoTierCORSMiddleware ──────────────────┐ │
│  │  /api/auth/*  → strict CORS (credentials=true, 明示 origin) │ │
│  │  その他       → permissive CORS (allow_origins=*, no creds) │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────── routers/auth.py (新規 10 endpoint) ───────────┐ │
│  │  login, refresh, logout, me, password,                      │ │
│  │  password-reset/{request,confirm},                          │ │
│  │  invitations/{token}, accept-invitation                     │ │
│  └─────────────────────────┬────────────────────────────────────┘ │
│                            │                                      │
│  ┌─────────────────────────▼────────────────────────────────┐    │
│  │            auth/provider.py (AuthProvider ABC)            │    │
│  │  authenticate / verify_token / get_user_by_email /        │    │
│  │  create_user / update_password / request_password_reset   │    │
│  │  + AuthContext (JWT / API キー統一)                       │    │
│  └────────┬────────────────────────────────┬─────────────────┘    │
│           │                                │                      │
│           ▼                                ▼                      │
│  ┌─────────────────┐              ┌──────────────────────────┐   │
│  │ providers/      │              │ providers/local.py       │   │
│  │ supabase.py     │              │  ┌────────────────────┐  │   │
│  │ (HTTP →         │              │  │ jwt_utils          │  │   │
│  │  Supabase API)  │              │  │ password           │  │   │
│  └─────────────────┘              │  │ tokens             │  │   │
│                                   │  │ rate_limit         │  │   │
│                                   │  └─────────┬──────────┘  │   │
│                                   └────────────┼─────────────┘   │
│                                                │                  │
│  ┌─────────────────────────────────────────────▼──────────────┐  │
│  │           email_backends/ (Null/Console/SMTP)               │  │
│  │  招待メール、パスワードリセットメール                        │  │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 既存ルーター (teams.py / api_keys.py / tilesets.py 等)       │  │
│  │  → require_auth() / get_current_user() インタフェース不変   │  │
│  │  → 内部実装が AuthProvider 経由になるだけ                   │  │
│  │  → タイル系は get_auth_context_optional に移行（API キー対応）│  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────┐
              │      PostgreSQL + PostGIS          │
              │  ┌─────────────────────────────┐  │
              │  │ users (新規・local 時のみ)   │  │
              │  │ refresh_tokens (新規)       │  │
              │  │ auth_login_attempts (新規)  │  │
              │  │ password_reset_tokens (新規)│  │
              │  │ teams / team_members /      │  │
              │  │ team_invitations / api_keys │  │
              │  │ tilesets / features / ...   │  │
              │  └─────────────────────────────┘  │
              └───────────────────────────────────┘
```

### 3.2 主要なデータフロー

**(A) ログイン (local プロバイダ)**

1. Admin UI → `POST /api/auth/login {email, password}`
2. `routers/auth.py` → `AuthProvider.authenticate(...)`
3. `LocalAuthProvider`:
   - `rate_limit.check_login_rate_limit(email, ip)`
   - `users` から SELECT
   - `password.verify_password(input, stored_hash)` （ユーザー不存在時もダミーハッシュで比較してタイミング差を消す）
   - 成功 → `jwt_utils.issue_access_token(user)` + `tokens.issue_refresh_token(user)`
4. レスポンス: `{access_token, expires_in: 900, user}` + `Set-Cookie: geo_base_refresh=...; HttpOnly; Path=/api/auth`
5. Admin UI は access_token をメモリに保持

**(B) 既存リクエストの認証**

1. クライアント → `Authorization: Bearer <access_token>` で `/api/tilesets` 等を呼ぶ
2. `Depends(require_auth)` → `AuthProvider.verify_access_token(token)` → `User`
3. ルーター本体は既存ロジックを実行（**変更なし**）

**(C) チーム招待受諾 (新規ユーザー、local モード)**

1. 管理者: `POST /api/teams/{id}/invitations {email, role}` → `team_invitations` 行作成 + 招待メール送信
2. 招待相手: メールリンクから `/accept-invitation?token=...` へ
3. ブラウザ: `GET /api/auth/invitations/{token}` で招待情報取得
4. ブラウザ: `POST /api/auth/accept-invitation {token, password, name}`
5. サーバー（トランザクション）:
   - 招待検証
   - `AuthProvider.create_user(email, password, name, email_verified=true)`
   - `team_members` に追加
   - `team_invitations.status = 'accepted'`
   - access + refresh token 発行（即時ログイン）

**(D) タイル取得 (API キー経由)**

1. クライアント → `Authorization: Bearer gb_live_...` で `/api/tiles/features/{z}/{x}/{y}.pbf`
2. `Depends(get_auth_context_optional)`:
   - トークンプレフィックス `gb_` を検出 → API キーパス
   - `validate_api_key()` SQL 関数で lookup
   - `is_active`, expiry, revoked 確認
   - レート制限カウンタ更新
   - `AuthContext.from_api_key(key_data)` を返す
3. `check_tileset_access_v2(tileset, ctx)`:
   - 公開タイルセット → 許可
   - オーナー一致 → 許可
   - キーの `team_id` がタイルセットの `team_tilesets` で共有されている → 許可
   - それ以外 → 403
4. タイル生成・返却 + `log_api_key_usage()` 非同期記録

**(E) AUTH_PROVIDER=supabase 時**

- `SupabaseAuthProvider` が `authenticate` を Supabase Auth REST API（`/auth/v1/token?grant_type=password`）に委譲
- `verify_access_token` は HS256 検証ロジック（既存と同じ）
- `create_user` は Supabase Auth Admin API（`/auth/v1/admin/users`）
- このモードでは geo-base の `users` テーブルは使われない

### 3.3 設計上の重要な決定

1. **既存ルーター（teams/api_keys/tilesets 等）は変更しない**: `require_auth` と `get_current_user` のシグネチャ・例外・戻り値は完全互換
2. **`AuthProvider` は起動時に1つだけ生成**: factory + `lru_cache` パターン
3. **Supabase モードでも geo-base のスキーマは同じ**: `users` テーブルだけ unused
4. **Admin UI からは `/api/auth/*` のみ叩く**: Supabase クライアント直叩きは全廃
5. **タイル系エンドポイントは `AuthContext` 対応へ段階移行**: JWT と API キーの統一処理

---

## 4. データベーススキーマ変更

### 4.1 新規テーブル（4つ）

#### `users` （local モード用）

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified_at TIMESTAMPTZ,                -- 招待受諾時に自動セット
    password_hash VARCHAR(255) NOT NULL,          -- bcrypt
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'authenticated',     -- JWT クレーム互換
    is_active BOOLEAN DEFAULT TRUE,
    app_metadata JSONB DEFAULT '{}',              -- Supabase 互換
    user_metadata JSONB DEFAULT '{}',             -- Supabase 互換
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT email_lowercase CHECK (email = LOWER(email))
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;
```

Supabase モードでは未使用。カラム構成は将来的な auth.users インポート時に互換性を持たせる。

#### `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,                        -- 意図的に FK なし
    token_hash VARCHAR(128) NOT NULL UNIQUE,      -- SHA-256
    user_agent VARCHAR(500),
    ip_address INET,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,              -- 30 日後
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(255),
    replaced_by UUID,                             -- ローテーション追跡
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

#### `auth_login_attempts`

```sql
CREATE TABLE auth_login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255),
    ip_address INET,
    success BOOLEAN NOT NULL,
    user_agent VARCHAR(500),
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_auth_login_attempts_email_time ON auth_login_attempts(email, attempted_at DESC);
CREATE INDEX idx_auth_login_attempts_ip_time ON auth_login_attempts(ip_address, attempted_at DESC);
```

#### `password_reset_tokens`

```sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,              -- 1 時間後
    used_at TIMESTAMPTZ,
    ip_address INET
);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
```

### 4.2 FK 制約方針: 追加しない

`team_members.user_id`, `teams.owner_id`, `team_invitations.invited_by`, `api_keys.user_id`, `refresh_tokens.user_id`, `password_reset_tokens.user_id` などは **すべて plain UUID で FK なし** を維持する。

理由:
- Supabase モードでは `users` テーブルが空 → FK を貼ると参照先が存在せず制約違反
- 同じ UUID 空間を local の `users.id` と Supabase の `auth.users.id` で共有する設計
- 既存の team/api_key スキーマも FK を貼っていない（一貫性）
- 整合性チェックが必要になればアプリ層 or トリガで対応（YAGNI）

### 4.3 スキーマファイル番号体系

```
docker/postgis-init/
├── 01_init.sql                       # 既存
├── 02_raster_schema.sql              # 既存
├── 03_pmtiles_schema.sql             # 既存
├── 04_auth_schema.sql                # 新規（本仕様で追加）
├── 05_teams_schema.sql               # 既存（番号維持）
├── 06_api_keys_schema.sql            # 既存（番号維持）
└── 09_rls_policies.sql               # 04_rls_policies.sql からリネーム
└── 09_rls_policies.sql.supabase      # 同上
```

`04_rls_policies.sql` を 09 にリネームする理由: RLS は全テーブル定義後に適用するのが自然な順序。

### 4.4 Helper SQL 関数とトリガ

`04_auth_schema.sql` に同梱:

- `cleanup_expired_refresh_tokens()` - 定期メンテナンス
- `cleanup_old_login_attempts()` - 24 時間以上前の記録削除
- `count_recent_failed_logins(p_email, p_window_minutes)` - レート制限判定

`users.updated_at` トリガは既存の `update_updated_at_column()` 関数（`01_init.sql` で定義済み）を使用する。`04_auth_schema.sql` は `01_init.sql` の後に実行される必要がある。

### 4.5 既存スキーマへの影響

- `05_teams_schema.sql` / `06_api_keys_schema.sql`: **変更なし**
- コメント文言の修正のみ（「Supabase auth.users のID」→「ユーザーID（local モードでは users.id、supabase モードでは auth.users.id）」）

---

## 5. AuthProvider インタフェースと 2 プロバイダ実装

### 5.1 共通の型定義

```python
# api/lib/auth/models.py
class User(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    app_metadata: Optional[dict] = None
    user_metadata: Optional[dict] = None
    name: Optional[str] = None
    email_verified: bool = False

class AuthResult(BaseModel):
    is_authenticated: bool
    user: Optional[User] = None
    error: Optional[str] = None

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
```

### 5.2 エラー階層

```python
# api/lib/auth/errors.py
class AuthError(Exception): ...
class InvalidCredentials(AuthError): ...
class RateLimited(AuthError): ...
class UserNotFound(AuthError): ...
class UserAlreadyExists(AuthError): ...
class InvalidToken(AuthError): ...
class WeakPassword(AuthError): ...
class ProviderError(AuthError): ...
```

ルーター層（`routers/auth.py`）で `AuthError` を catch して `HTTPException` に翻訳。

### 5.3 AuthProvider ABC

```python
# api/lib/auth/provider.py
class AuthProvider(ABC):
    @abstractmethod
    async def verify_access_token(self, token: str) -> AuthResult: ...
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]: ...
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]: ...
    @abstractmethod
    async def authenticate(self, email: str, password: str,
        ip: Optional[str] = None, user_agent: Optional[str] = None) -> TokenPair: ...
    @abstractmethod
    async def refresh_tokens(self, refresh_token: str,
        ip: Optional[str] = None, user_agent: Optional[str] = None) -> TokenPair: ...
    @abstractmethod
    async def revoke_refresh_token(self, refresh_token: str) -> None: ...
    @abstractmethod
    async def create_user(self, email: str, password: str,
        name: Optional[str] = None, email_verified: bool = False,
        app_metadata: Optional[dict] = None, user_metadata: Optional[dict] = None) -> User: ...
    @abstractmethod
    async def update_user(self, user_id: str,
        name: Optional[str] = None, email: Optional[str] = None,
        user_metadata: Optional[dict] = None) -> User: ...
    @abstractmethod
    async def update_password(self, user_id: str, new_password: str) -> None: ...
    @abstractmethod
    async def request_password_reset(self, email: str, ip: Optional[str] = None) -> None: ...
    @abstractmethod
    async def confirm_password_reset(self, token: str, new_password: str) -> User: ...
```

### 5.4 ファクトリ

```python
# api/lib/auth/__init__.py
@lru_cache(maxsize=1)
def get_auth_provider() -> AuthProvider:
    settings = get_settings()
    if settings.auth_provider == "local":
        from .providers.local import LocalAuthProvider
        return LocalAuthProvider()
    elif settings.auth_provider == "supabase":
        from .providers.supabase import SupabaseAuthProvider
        return SupabaseAuthProvider()
    raise ValueError(f"Unknown AUTH_PROVIDER: {settings.auth_provider}")
```

`require_auth` / `get_current_user` は内部実装だけ書き換え、シグネチャ互換維持。

### 5.5 SupabaseAuthProvider 実装方針

- `httpx.AsyncClient` で Supabase Auth REST API を呼び出す
- 必要な環境変数: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`

| メソッド | Supabase API |
|---|---|
| `verify_access_token` | ローカルで HS256 検証 |
| `authenticate` | `POST /auth/v1/token?grant_type=password` |
| `refresh_tokens` | `POST /auth/v1/token?grant_type=refresh_token` |
| `revoke_refresh_token` | `POST /auth/v1/logout` |
| `create_user` | `POST /auth/v1/admin/users` |
| `get_user_by_email` | `GET /auth/v1/admin/users?filter=email=eq.{email}` |
| `get_user_by_id` | `GET /auth/v1/admin/users/{id}` |
| `update_user` / `update_password` | `PUT /auth/v1/admin/users/{id}` |
| `request_password_reset` | `POST /auth/v1/recover` |
| `confirm_password_reset` | recovery token → verifyOtp 系 API |

password reset メールは Supabase 側が送信する（geo-base の email_backend は使わない）。

### 5.6 LocalAuthProvider 実装方針

- DB（4 テーブル）と共有ユーティリティを組み合わせる

| メソッド | 実装 |
|---|---|
| `verify_access_token` | `jwt_utils.decode_access_token(token, secret, audience)` |
| `authenticate` | `rate_limit.check` → `users` 検索 → `password.verify` → 成功時 `jwt_utils.issue_access_token` + `tokens.issue_refresh_token` |
| `refresh_tokens` | `tokens.verify_and_rotate_refresh_token` |
| `revoke_refresh_token` | `tokens.revoke_refresh_token` |
| `create_user` | `password.hash_password` → INSERT users（重複は `UserAlreadyExists`） |
| `request_password_reset` | `password_reset_tokens` 発行 → `email_backend.send` |
| `confirm_password_reset` | token 検証 → `password.hash_password` → UPDATE + token 失効 + 全 refresh 失効 |

### 5.7 ファイル構成

```
api/lib/auth/
├── __init__.py              # 公開 API: User, AuthResult, get_auth_provider, 
│                            #   require_auth, get_current_user, AuthContext, 
│                            #   get_auth_context_optional, require_auth_context
├── models.py                # User, AuthResult, TokenPair
├── errors.py                # AuthError 階層
├── provider.py              # AuthProvider ABC
├── context.py               # AuthContext（JWT / API キー統一）
├── api_key_auth.py          # API キー検証 + AuthContext 生成 + レート制限統合
├── providers/
│   ├── __init__.py
│   ├── supabase.py
│   └── local.py
├── jwt_utils.py
├── password.py
├── tokens.py
├── rate_limit.py
├── email_backends/
│   ├── __init__.py
│   ├── null_backend.py
│   ├── console_backend.py
│   ├── smtp_backend.py
│   └── templates.py
└── cli.py                   # python -m lib.auth.cli
```

### 5.8 既存 `auth.py` の移行

現状 `api/lib/auth.py`（327 行）を分解:
1. 新規ディレクトリ `api/lib/auth/` を作成し、ファイル群を配置
2. `auth/__init__.py` で既存の公開シンボルをすべて re-export
3. **同一コミットで** 古い `auth.py` を削除（`auth.py` と `auth/` が両方存在すると Python の解決順序が実装依存になるため、**両方が共存する状態を残してはいけない**）
4. 既存 import 文（`from lib.auth import User` 等）は変更不要 — `auth/__init__.py` の re-export で互換

---

## 6. 共有ユーティリティの責務と境界

### 6.1 `jwt_utils.py`（~80 行）

```python
def issue_access_token(user, *, secret, audience, issuer="geo-base", ttl_seconds=900) -> str
def decode_access_token(token, *, secret, audience) -> dict
def claims_to_user(claims) -> User
```

純粋関数、依存は `pyjwt` のみ。

### 6.2 `password.py`（~50 行）

```python
MIN_PASSWORD_LENGTH = 8
BCRYPT_ROUNDS = 12

def hash_password(plaintext) -> str
def verify_password(plaintext, hash) -> bool   # 定時間比較
def check_password_policy(plaintext) -> None
```

依存: `passlib[bcrypt]`。ポリシー: 最小 8 文字 + 英字 + 数字または記号。NIST SP 800-63B 準拠で過度な複雑性は要求しない。

### 6.3 `tokens.py`（~150 行）

```python
REFRESH_TOKEN_TTL_DAYS = 30

def issue_refresh_token(conn, user_id, *, ip=None, user_agent=None) -> str
def verify_and_rotate_refresh_token(conn, refresh_token, *, ip=None, user_agent=None) -> tuple[str, str]
def revoke_refresh_token(conn, refresh_token, reason="logout") -> None
def revoke_all_user_tokens(conn, user_id, reason) -> int
def cleanup_expired_tokens(conn) -> int
```

**重要**: トークンローテーション + 再利用検知。revoked 済みトークンが再提示された場合、そのユーザーの全トークンを失効（盗難検知）。`SELECT ... FOR UPDATE` で並行 race を防ぐ。

### 6.4 `rate_limit.py`（~70 行）

```python
MAX_FAILED_ATTEMPTS = 5
WINDOW_MINUTES = 15

def check_login_rate_limit(conn, *, email=None, ip=None) -> None
def record_login_attempt(conn, *, email, success, ip=None, user_agent=None) -> None
def cleanup_old_attempts(conn) -> int
```

DB ベース（`auth_login_attempts` テーブル）。email or IP のいずれかが閾値超過でロック。

### 6.5 `email_backends/`

```python
class EmailBackend(ABC):
    @abstractmethod
    async def send(self, to, subject, body) -> None
```

- `null_backend.py`: 内部リストに記録（テスト用）
- `console_backend.py`: 標準出力 + `logger.info`
- `smtp_backend.py`: `smtplib.SMTP` で TLS 送信、外部 SDK 不要
- `templates.py`: `render_invitation_email`, `render_password_reset_email`（プレーンテキストのみ）

### 6.6 `cli.py`

```bash
uv run python -m lib.auth.cli create-admin --email <email>
uv run python -m lib.auth.cli revoke-user-tokens <user_id>
uv run python -m lib.auth.cli cleanup-expired
uv run python -m lib.auth.cli reset-password --email <email>
uv run python -m lib.auth.cli list-users [--json]
```

`argparse` のサブコマンド方式。`getpass` でパスワード非表示入力。

### 6.7 モジュール依存グラフ

```
provider.py (ABC)
  ↑
  ├── providers/local.py
  │     ↓ uses
  │   ┌── jwt_utils.py
  │   ├── password.py
  │   ├── tokens.py
  │   ├── rate_limit.py
  │   └── email_backends/
  │
  └── providers/supabase.py
        ↓ uses
        ├── jwt_utils.py (検証のみ)
        └── httpx (外部)
```

循環依存なし。各ユーティリティは自己完結。

### 6.8 サイズ感

| 部品 | 行数目安 |
|---|---|
| `jwt_utils.py` | ~80 |
| `password.py` | ~50 |
| `tokens.py` | ~150 |
| `rate_limit.py` | ~70 |
| `email_backends/*` | ~210 |
| `providers/local.py` | ~300 |
| `providers/supabase.py` | ~250 |
| `provider.py` | ~100 |
| `models.py` | ~50 |
| `errors.py` | ~30 |
| `context.py` | ~40 |
| `api_key_auth.py` | ~150 |
| `cli.py` | ~80 |
| **合計** | **約 1,560 行** |

---

## 7. API エンドポイントとルーター変更

### 7.1 新規ルーター: `api/lib/routers/auth.py`

prefix `/api/auth`、10 エンドポイント:

| # | メソッド + パス | 認証 | 用途 |
|---|---|---|---|
| 1 | `POST /api/auth/login` | なし | ログイン |
| 2 | `POST /api/auth/refresh` | Cookie | アクセストークン更新（rotation） |
| 3 | `POST /api/auth/logout` | Cookie | ログアウト |
| 4 | `GET /api/auth/me` | Bearer | 自分のユーザー情報 |
| 5 | `PATCH /api/auth/me` | Bearer | プロフィール更新 |
| 6 | `POST /api/auth/me/password` | Bearer | パスワード変更 |
| 7 | `POST /api/auth/password-reset/request` | なし | リセットメール送信要求 |
| 8 | `POST /api/auth/password-reset/confirm` | なし | リセット完了 |
| 9 | `GET /api/auth/invitations/{token}` | なし | 招待情報取得 |
| 10 | `POST /api/auth/accept-invitation` | なし | 招待経由のサインアップ |

### 7.2 エンドポイント仕様

#### POST /api/auth/login
```
Body: { email, password }
Resp: 200 { access_token, expires_in: 900, token_type: "Bearer", user }
      Set-Cookie: geo_base_refresh; HttpOnly; SameSite=Lax|None; Secure (prod);
                  Path=/api/auth; Max-Age=2592000
Err:  401 InvalidCredentials, 429 RateLimited
```

#### POST /api/auth/refresh
```
Cookie in:  geo_base_refresh
Cookie out: geo_base_refresh (rotated)
Resp: 200 { access_token, expires_in, token_type, user }
Err:  401 InvalidToken（盗難検知時は同ユーザー全失効）
```

#### POST /api/auth/logout
```
Cookie in:  geo_base_refresh (任意)
Resp: 204
      Set-Cookie: geo_base_refresh; Max-Age=0
冪等
```

#### GET /api/auth/me
```
Header: Authorization Bearer
Resp: 200 User
Err:  401
```
※ 既存の `routers/health.py` から移設

#### PATCH /api/auth/me
```
Header: Authorization Bearer
Body: { name?, email?, user_metadata? }
Resp: 200 User
Err:  401, 400, 409 (email 重複)
```
注: email 変更は即時反映、再検証メールは送らない（Phase 4 課題）

#### POST /api/auth/me/password
```
Header: Authorization Bearer
Body: { current_password, new_password }
Resp: 204
Err:  401 (current 不一致), 400 WeakPassword
Side: 全 refresh token 失効
```

#### POST /api/auth/password-reset/request
```
Body: { email }
Resp: 204 (常に成功 — 情報漏洩防止)
Side: ユーザー存在時に password_reset_tokens 発行 + email 送信
```

#### POST /api/auth/password-reset/confirm
```
Body: { token, new_password }
Resp: 204
Err:  400 InvalidToken, 400 WeakPassword
Side: パスワード更新 + 全 refresh token 失効
```

#### GET /api/auth/invitations/{token}
```
Resp: 200 {
  team_id, team_name, team_slug, role, email, inviter_name,
  expires_at, has_existing_account: bool
}
Err: 404
```

#### POST /api/auth/accept-invitation
```
Body: { token, password, name }
Resp: 201 { access_token, expires_in, token_type, user, team_member: { team_id, role } }
      Set-Cookie: geo_base_refresh
Err:  400 InvalidToken, 400 WeakPassword,
      409 UserAlreadyExists (既存メール → 既存アカウントでログイン後に /api/teams/invitations/accept を使えとヒント)
Side: AuthProvider.create_user → team_members 追加 → invitation accepted（トランザクション）
```

### 7.3 既存ルーターの変更

#### `routers/health.py`
- 削除: `/api/auth/me`, `/api/auth/status`（あれば）
- 残す: `/api/health`, `/api/health/db`

#### `routers/teams.py`
1. `POST /api/teams/invitations/accept`: `user.email == invitation.email` を **追加検証**
2. `POST /api/teams/{id}/invitations`: 招待作成時に email 送信処理を追加（既存ロジック後に挿入、送信失敗は招待作成自体を失敗させない）

#### `main.py`
- `auth_router` を include に追加
- `CORSMiddleware` を `TwoTierCORSMiddleware` に差し替え

#### タイル系ルーター
- `routers/tiles/dynamic.py`, `pmtiles.py`, `raster.py`, `mbtiles.py`: dependency を `get_auth_context_optional` に変更
- `routers/tilesets.py`: tilejson エンドポイント等で同様

#### その他（features.py, datasources.py 等）
- 変更なし

### 7.4 Cookie 戦略

| 項目 | 値 |
|---|---|
| 名前 | `geo_base_refresh` |
| HttpOnly | ✅ |
| SameSite | Lax (local) / None (本番 cross-origin) |
| Secure | false (local) / true (本番) |
| Path | `/api/auth`（防御の深さ） |
| Max-Age | 2,592,000 秒（30 日） |

### 7.5 招待フロー全体

```
[管理者]                          [被招待者]
   POST /api/teams/{id}/invitations
   { email, role, message }
        ↓
        201 + email 送信
                                    リンククリック → /accept-invitation?token=...
                                    GET /api/auth/invitations/{token}
                                    ← 200 { team_name, role, has_existing_account }
                          ┌────────────┴────────────┐
                  has_existing_account          has_existing_account
                  = false                       = true
                          │                         │
                  サインアップフォーム            ログインフォーム
                  POST /api/auth/                POST /api/auth/login
                    accept-invitation            ↓ access_token
                  { token, password,             POST /api/teams/invitations/accept
                    name }                       { token }
                  ← 201 + tokens                 ← 200 team_member
                    (auto login)                  
                          │                         │
                          ▼                         ▼
                       ダッシュボード遷移
```

---

## 8. Admin UI 認証層（Supabase 抜き）

### 8.1 ファイル構成

```
app/src/
├── middleware.ts                          # ルートガード
├── lib/
│   ├── api.ts                             # 既存修正
│   └── auth/
│       ├── client.ts                      # AuthClient シングルトン
│       ├── context.tsx                    # AuthProvider, useAuth() フック
│       ├── types.ts
│       └── errors.ts
├── app/
│   ├── layout.tsx                         # AuthProvider でラップ
│   ├── login/page.tsx                     # 修正
│   ├── accept-invitation/page.tsx         # 新規
│   ├── password-reset/
│   │   ├── request/page.tsx               # 新規
│   │   └── confirm/page.tsx               # 新規
│   ├── settings/
│   │   ├── profile/page.tsx               # 新規
│   │   └── password/page.tsx              # 新規
│   └── (既存ページ無変更)
├── components/
│   └── auth/
│       ├── login-form.tsx
│       ├── invitation-signup-form.tsx
│       └── password-reset-form.tsx
└── (削除)
    └── lib/supabase/                      # 丸ごと削除
```

### 8.2 AuthClient

```typescript
class AuthClient {
  private accessToken: string | null = null;
  private refreshTimer: number | null = null;
  private listeners: Set<(s: AuthState) => void> = new Set();

  async login(email, password): Promise<User>
  async refresh(): Promise<User | null>
  async logout(): Promise<void>
  getAccessToken(): string | null
  subscribe(listener): () => void
}

export const authClient = new AuthClient();
```

性質:
- アクセストークンはメモリ内のみ（XSS 耐性）
- リフレッシュは TTL 60 秒前に自動実行
- ページリロードで access_token 消失 → refresh cookie から再取得

### 8.3 React Context

```typescript
'use client';
export function AuthProvider({ children }) {
  const [state, setState] = useState({ user: null, isLoading: true, isAuthenticated: false });
  useEffect(() => {
    authClient.refresh().finally(() => setState(s => ({ ...s, isLoading: false })));
    return authClient.subscribe(setState);
  }, []);
  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
```

### 8.4 Middleware

```typescript
const PROTECTED_PATHS = ['/tilesets', '/features', '/datasources', '/teams', '/api-keys', '/settings'];
const AUTH_PAGES = ['/login', '/password-reset/request', '/password-reset/confirm'];

export function middleware(request) {
  const hasRefreshCookie = !!request.cookies.get('geo_base_refresh');
  const { pathname } = request.nextUrl;

  if (PROTECTED_PATHS.some(p => pathname.startsWith(p)) && !hasRefreshCookie) {
    return NextResponse.redirect(new URL(`/login?next=${pathname}`, request.url));
  }
  if (AUTH_PAGES.includes(pathname) && hasRefreshCookie) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  return NextResponse.next();
}
```

middleware は Cookie 存在チェックのみ。本物の検証は AuthClient のマウント時 `refresh()` で行う。

### 8.5 lib/api.ts 修正

```typescript
async function apiFetch(path, options = {}) {
  const token = authClient.getAccessToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  
  let res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: 'include' });
  
  if (res.status === 401 && token) {
    const refreshed = await authClient.refresh();
    if (refreshed) {
      headers.set('Authorization', `Bearer ${authClient.getAccessToken()}`);
      res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: 'include' });
    }
  }
  return res;
}
```

### 8.6 クロスオリジン Cookie 対策

**ローカル開発**: Next.js rewrites で同一 origin 化。

```js
// app/next.config.js
async rewrites() {
  if (process.env.NODE_ENV === 'development') {
    return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
  }
  return [];
}
```

**本番**: `SameSite=None; Secure` + CORS で Admin UI ドメインを明示許可。

### 8.7 認証フロー画面

| パス | 役割 |
|---|---|
| `/login` | Email + Password、`?next=` クエリ対応 |
| `/accept-invitation?token=...` | 招待情報フェッチ → 新規 or 既存ユーザー分岐 |
| `/password-reset/request` | Email フォーム、結果は常に同じメッセージ |
| `/password-reset/confirm?token=...` | 新パスワード入力 |
| `/settings/profile` | プロフィール変更 |
| `/settings/password` | パスワード変更 |

### 8.8 package.json 変更

削除:
```json
"@supabase/ssr": "^0.5.2",
"@supabase/supabase-js": "^2.48.1"
```

### 8.9 環境変数

`.env.local` から削除: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### 8.10 サイズ感

| 部品 | 行数目安 |
|---|---|
| `lib/auth/client.ts` | ~150 |
| `lib/auth/context.tsx` | ~50 |
| `middleware.ts` | ~40 |
| `lib/api.ts` 追加分 | ~50 |
| 各認証ページ | ~80〜120 |
| 各認証コンポーネント | ~80〜120 |
| **合計** | **新規 ~800〜1,000、削除 ~300** |

---

## 9. 設定・ブートストラップ・運用

### 9.1 環境変数（API）

```bash
# 認証プロバイダ
AUTH_PROVIDER=local                   # local | supabase

# JWT（local 必須、supabase は SUPABASE_JWT_SECRET にフォールバック）
JWT_SECRET=                           # openssl rand -base64 64
JWT_AUDIENCE=authenticated
JWT_ISSUER=geo-base
ACCESS_TOKEN_TTL_SECONDS=900

# メール
EMAIL_BACKEND=console                 # null | console | smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true

# 招待リンク
INVITATION_BASE_URL=http://localhost:3000

# Cookie
COOKIE_SAMESITE=lax                   # lax | none
COOKIE_SECURE=false
COOKIE_DOMAIN=

# CORS
CORS_ORIGINS=http://localhost:3000    # カンマ区切り

# API キー使用ログサンプリング
API_KEY_LOG_SAMPLE_RATE=1.0           # 0.0〜1.0
```

### 9.2 起動時バリデーション

```python
@model_validator(mode='after')
def validate_auth_config(self):
    if self.auth_provider == "local" and not self.effective_jwt_secret:
        raise ValueError("AUTH_PROVIDER=local requires JWT_SECRET")
    if self.auth_provider == "supabase":
        for f in ['supabase_url', 'supabase_service_role_key', 'supabase_jwt_secret']:
            if not getattr(self, f):
                raise ValueError(f"AUTH_PROVIDER=supabase requires {f.upper()}")
    if self.email_backend == "smtp" and (not self.smtp_host or not self.smtp_from):
        raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST and SMTP_FROM")
    if self.cookie_samesite == "none" and not self.cookie_secure:
        raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
    return self

@property
def effective_jwt_secret(self):
    return self.jwt_secret or self.supabase_jwt_secret
```

### 9.3 CLI

```bash
uv run python -m lib.auth.cli create-admin --email admin@example.com
uv run python -m lib.auth.cli revoke-user-tokens <user_id>
uv run python -m lib.auth.cli cleanup-expired
uv run python -m lib.auth.cli reset-password --email <email>
uv run python -m lib.auth.cli list-users [--json]
```

### 9.4 ブートストラップ（local モード初回）

```bash
# 1. PostGIS 起動
cd docker && docker compose up -d

# 2. API 環境変数
cd ../api
cat > .env <<EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base
AUTH_PROVIDER=local
JWT_SECRET=$(openssl rand -base64 64)
EMAIL_BACKEND=console
INVITATION_BASE_URL=http://localhost:3000
EOF

# 3. 依存
uv sync

# 4. 初期管理者
uv run python -m lib.auth.cli create-admin --email admin@example.com

# 5. API 起動
uv run uvicorn lib.main:app --reload --port 8000

# 6. Admin UI
cd ../app && npm install && npm run dev
```

### 9.5 本番カットオーバー（supabase → local）

greenfield 前提のため簡素:

```bash
# 1. デプロイ済みコード（AUTH_PROVIDER=supabase）はそのまま
# 2. 初期管理者作成
fly ssh console -C "cd /app && uv run python -m lib.auth.cli create-admin --email <admin>"

# 3. プロバイダ切替
fly secrets set AUTH_PROVIDER=local

# 4. ヘルスチェック
curl https://geo-base-api.fly.dev/api/health

# 5. Admin UI で新 admin にてログイン確認
```

### 9.6 周期メンテナンス

cron で日次実行（Fly.io scheduled machines or 外部 cron）:

```bash
0 3 * * * cd /app && uv run python -m lib.auth.cli cleanup-expired
```

### 9.7 ドキュメント更新

| ファイル | 内容 |
|---|---|
| `docs/AUTH_SETUP.md`（新規） | 認証完全ガイド |
| `docs/AUTH_MIGRATION.md`（新規） | supabase → local 移行手順 |
| `LOCAL_DEVELOPMENT.md` | 環境変数・CLI 紹介・Supabase 削除 |
| `api/README.md` | プロジェクト構造、新エンドポイント |
| `app/README.md` | Supabase 撤去、middleware 説明 |
| `CLAUDE.md` | 認証プロバイダ・環境変数セクション |
| `HANDOVER_S3.md` | Step 3.3-A 進捗更新 |
| `docs/INFRA_MIGRATION_INVESTIGATION.md` | 「準備工程」を実績で更新 |

### 9.8 設定マトリクス

| シナリオ | AUTH_PROVIDER | EMAIL_BACKEND | COOKIE_SECURE | COOKIE_SAMESITE | CORS_ORIGINS |
|---|---|---|---|---|---|
| ローカル + Supabase | supabase | console | false | lax | localhost:3000 |
| ローカル + 素の Postgres | local | console | false | lax | localhost:3000 |
| 本番（現状維持） | supabase | console | true | none | geo-base-admin.vercel.app |
| 本番（カットオーバー後） | local | smtp | true | none | geo-base-admin.vercel.app |

---

## 10. エラーハンドリング・セキュリティ

### 10.1 脅威モデルと対策

| # | 脅威 | 対策 |
|---|---|---|
| 1 | ブルートフォースログイン | 5回失敗/15分でロック（`rate_limit.py`） |
| 2 | リフレッシュトークン盗難 | rotation + 再利用検知（盗難検出時にユーザー全失効） |
| 3 | XSS によるトークン窃取 | アクセストークンはメモリのみ、リフレッシュは HttpOnly Cookie |
| 4 | CSRF | SameSite + Path 制限 + Origin ヘッダ検証（refresh/logout） |
| 5 | アカウント列挙（login） | エラーメッセージ統一 + ダミーパスワード比較 |
| 6 | アカウント列挙（reset） | 常に 204 |
| 7 | タイミング攻撃 | bcrypt 定時間 + ユーザー不存在時もダミーハッシュ比較 |
| 8 | リセットリンク詐取 | 設定値 `INVITATION_BASE_URL` から組立、Host ヘッダ不使用 |
| 9 | JWT 鍵漏洩 | `JWT_SECRET` を Fly secrets で管理、ログ出力禁止 |
| 10 | リプレイ攻撃 | 短命 access (15分) + refresh rotation |
| 11 | セッションフィクセーション | サーバー生成のみ |
| 12 | 招待権限昇格 | `invitation.email == request.email` 強制、role はクライアント送信値無視 |
| 13 | オープンリダイレクト | `next` クエリは相対 URL のみ許可 |
| 14 | SQL インジェクション | パラメータ化クエリ統一 |
| 15 | API キー誤用 | API キーは `/api/auth/*` で使用不可 |
| 16 | メール経由 XSS | プレーンテキストのみ |
| 17 | リフレッシュ盗難検出遅延 | revoked トークン再提示で全失効 |

### 10.2 エラー翻訳パターン

```python
ERROR_MAP = {
    InvalidCredentials:    (401, "Invalid email or password"),
    RateLimited:           (429, "Too many failed attempts. Try again later."),
    InvalidToken:          (401, "Invalid or expired token"),
    UserAlreadyExists:     (409, "An account with this email already exists"),
    UserNotFound:          (404, "User not found"),
    WeakPassword:          (400, lambda e: f"Password policy violation: {e}"),
    ProviderError:         (502, "Authentication service unavailable"),
}
```

### 10.3 リフレッシュトークン rotation アルゴリズム

```python
def verify_and_rotate_refresh_token(conn, refresh_token, ip=None, user_agent=None):
    token_hash = sha256(refresh_token)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, user_id, revoked_at, expires_at FROM refresh_tokens 
            WHERE token_hash = %s FOR UPDATE
        """, (token_hash,))
        row = cur.fetchone()
        if row is None:
            raise InvalidToken("Token not found")
        token_id, user_id, revoked_at, expires_at = row
        
        # 再利用検知: revoked 済みトークンが提示された
        if revoked_at is not None:
            logger.warning("Refresh token reuse detected", extra={"user_id": user_id})
            revoke_all_user_tokens(conn, user_id, reason="theft_detected")
            raise InvalidToken("Token has been revoked")
        
        if expires_at < now():
            cur.execute("UPDATE refresh_tokens SET revoked_at = NOW(), revoked_reason = 'expired' WHERE id = %s", (token_id,))
            raise InvalidToken("Token expired")
        
        # 新トークン発行
        new_token = secrets.token_urlsafe(48)
        new_token_hash = sha256(new_token)
        cur.execute("""
            INSERT INTO refresh_tokens (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + INTERVAL '30 days')
            RETURNING id
        """, (user_id, new_token_hash, ip, user_agent))
        new_token_id = cur.fetchone()[0]
        
        # 旧トークンを revoked + replaced_by
        cur.execute("""
            UPDATE refresh_tokens 
            SET revoked_at = NOW(), revoked_reason = 'rotated', replaced_by = %s 
            WHERE id = %s
        """, (new_token_id, token_id))
    conn.commit()
    return user_id, new_token
```

### 10.4 ログ出力ポリシー

**残す**: ログイン試行、トークン rotation、再利用検知（WARN）、リセット要求、ユーザー作成、プロバイダエラー、設定検証エラー。

**残さない**: 平文パスワード、bcrypt ハッシュ、JWT/refresh/reset トークンの全文、メール本文。

### 10.5 Origin ヘッダ検証

```python
def _check_origin(request, allowed):
    origin = request.headers.get("origin")
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin not allowed")
```

`refresh` と `logout` のみ。`login`/`password-reset/*`/`accept-invitation` はメール経由リンクのため Origin 無しを許容。

### 10.6 CORS（TwoTierCORSMiddleware）

```python
class TwoTierCORSMiddleware:
    """/api/auth/* は strict、それ以外は permissive"""
    def __init__(self, app, strict_origins):
        self._strict = CORSMiddleware(app, allow_origins=strict_origins, 
                                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
        self._public = CORSMiddleware(app, allow_origins=["*"],
                                       allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/api/auth/"):
            await self._strict(scope, receive, send)
        else:
            await self._public(scope, receive, send)
```

### 10.7 統一認証コンテキスト

```python
class AuthContext(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[str] = None       # API キーが特定のチームに紐付いている場合のみセット。
                                         # JWT ユーザーは常に None（所属チームは team_members を別途参照）
    scopes: list[str] = []
    is_api_key: bool = False
    api_key_id: Optional[str] = None
    
    @classmethod
    def from_jwt_user(cls, user) -> "AuthContext": ...
    
    @classmethod
    def from_api_key(cls, key_data) -> "AuthContext": ...
    
    def has_scope(self, required: str) -> bool:
        """admin > delete > write > read 階層"""
```

### 10.8 認証ディスパッチ

```python
async def get_auth_context_optional(authorization=Header(None), request=None) -> Optional[AuthContext]:
    if not authorization:
        return None
    token = extract_token_from_header(authorization)
    if not token:
        return None
    
    if token.startswith(API_KEY_PREFIX):  # "gb_"
        return await _validate_api_key(token, request=request)
    else:
        result = await get_auth_provider().verify_access_token(token)
        if result.is_authenticated and result.user:
            return AuthContext.from_jwt_user(result.user)
    return None
```

### 10.9 タイル認可ルール

```python
async def check_tileset_access_v2(conn, tileset, ctx: Optional[AuthContext]) -> bool:
    if tileset['is_public']:
        return True
    if ctx is None:
        return False
    if not ctx.has_scope("read"):
        return False
    if ctx.user_id == str(tileset['user_id']):
        return True
    if ctx.is_api_key and ctx.team_id:
        return await _is_tileset_shared_with_team(conn, tileset['id'], ctx.team_id)
    if not ctx.is_api_key:
        return await _user_has_team_access(conn, ctx.user_id, tileset['id'])
    return False
```

### 10.10 API キーレート制限とログ

- 既存 `api_key_rate_limits` テーブルでカウンタ更新
- `api_key_usage_logs` でリクエスト記録（**サンプリング率 `API_KEY_LOG_SAMPLE_RATE` で制御**、デフォルト 1.0、本番 0.1 推奨）
- レート超過 → 429
- Phase 4 で Redis 経由の非同期書き込みに改善

### 10.11 パスワードポリシー

```python
def check_password_policy(plaintext):
    if len(plaintext) < 8:
        raise WeakPassword("Password must be at least 8 characters")
    has_letter = any(c.isalpha() for c in plaintext)
    has_digit_or_symbol = any(c.isdigit() or not c.isalnum() for c in plaintext)
    if not (has_letter and has_digit_or_symbol):
        raise WeakPassword("Password must contain at least one letter and one digit or symbol")
```

NIST SP 800-63B 準拠（過度な複雑性は要求しない）。

### 10.12 セッション失効チャネル

| トリガ | 範囲 |
|---|---|
| `POST /api/auth/logout` | 該当 refresh token のみ |
| `POST /api/auth/me/password` | 該当ユーザー全失効 |
| `POST /api/auth/password-reset/confirm` | 該当ユーザー全失効 |
| トークン再利用検知 | 該当ユーザー全失効 |
| CLI `revoke-user-tokens` | 該当ユーザー全失効 |

---

## 11. テスト戦略

### 11.1 テスト階層

| 階層 | 対象 | DB | ネット | 件数 |
|---|---|---|---|---|
| ユニット | 純粋関数・モデル | ✗ | ✗ | ~120 |
| 統合（DB） | tokens, rate_limit, LocalAuthProvider | ✓ | ✗ | ~110 |
| プロバイダ（HTTP モック） | SupabaseAuthProvider | ✗ | mock | ~25 |
| ルーター | `/api/auth/*`、タイル認可 | ✓ | ✗ | ~55 |
| E2E（TestClient） | シナリオ | ✓ | ✗ | ~25 |
| CLI | スモーク | ✓ | ✗ | ~10 |
| **合計** | | | | **~350** |

### 11.2 ファイル配置

```
api/tests/
├── conftest.py
├── test_auth/
│   ├── test_jwt_utils.py / test_password.py / test_tokens.py / test_rate_limit.py
│   ├── test_email_backends.py / test_email_templates.py
│   ├── test_models.py / test_errors.py / test_context.py
│   ├── test_local_provider.py / test_supabase_provider.py
│   ├── test_api_key_auth.py / test_factory.py / test_cli.py
│   └── test_cors_middleware.py
├── test_routers/
│   ├── test_auth_routes.py
│   └── test_tile_access.py
├── test_integration/
│   ├── test_login_flow.py / test_invitation_flow.py
│   ├── test_password_reset_flow.py / test_team_access.py
└── test_provider_contract.py             # 両プロバイダ共通契約
```

### 11.3 必須セキュリティシナリオ（35 件）

ログイン、リフレッシュ、ログアウト、パスワード変更・リセット、招待、JWT 検証、CORS、API キー、タイル認可、設定検証、CLI のセキュリティ重要パスを網羅（詳細は本文セクション 11 を参照）。

### 11.4 共通契約テスト

```python
@pytest.fixture(params=["local", "supabase"])
async def auth_provider(request, db_conn, mock_supabase): ...

class TestProviderContract:
    """両プロバイダで同じ振る舞いを保証"""
    async def test_authenticate_invalid_credentials_same_error(self, auth_provider): ...
    async def test_create_user_returns_user_with_id(self, auth_provider): ...
    # 等
```

### 11.5 モック戦略

| 対象 | ツール |
|---|---|
| Supabase HTTP API | `respx` |
| 時刻 | `freezegun` |
| メール | `NullEmailBackend`（プロダクションコード） |
| DB | psycopg2 + 既存 conftest トランザクション |

### 11.6 conftest.py 追加フィクスチャ

`null_email_backend`, `local_auth_settings`, `make_user`, `make_team`, `make_invitation`, `make_api_key`, `authenticated_client` 等。

### 11.7 開発依存追加（`api/pyproject.toml`）

```toml
dev = [
    # 既存 ...
    "respx>=0.21.0",
    "freezegun>=1.4.0",
]
```

`passlib[bcrypt]` は本番依存に追加。

### 11.8 カバレッジ目標

| 部品 | 目標 |
|---|---|
| `jwt_utils`, `password`, `errors`, `models` | ≥ 95% |
| `tokens`, `rate_limit`, `email_backends/*` | ≥ 90% |
| Provider 実装 | ≥ 85% |
| Routers | ≥ 85% |
| **全体** | **≥ 85%** |

### 11.9 マーカー

```python
@pytest.mark.security
@pytest.mark.contract
@pytest.mark.integration
@pytest.mark.slow
```

CI: `pytest -m "not slow"` で短時間、夜間で全件。

### 11.10 Phase 3 でテストしない範囲

- 実 Supabase API への接続（モックのみ）
- 実 SMTP 送信（NullBackend のみ）
- Admin UI フロントエンド（Phase 4 で Playwright）
- 負荷・性能テスト
- ペネトレーションテスト

---

## 12. 移行・ロールアウト計画

### 12.1 段階的実装の順序

1. **DB スキーマ** (`04_auth_schema.sql` + `09_rls_policies.sql` リネーム)
2. **共有ユーティリティ** (`jwt_utils`, `password`, `tokens`, `rate_limit`, `email_backends/*`)
3. **AuthProvider ABC + LocalAuthProvider**
4. **SupabaseAuthProvider** (既存 `verify_jwt_token` 等を移設)
5. **既存 `auth.py` を `auth/` パッケージに分割** (互換 re-export)
6. **`AuthContext` + API キー認証** (`context.py`, `api_key_auth.py`)
7. **`routers/auth.py`** (10 エンドポイント)
8. **`TwoTierCORSMiddleware` + `main.py` 修正**
9. **タイル系ルーターを `AuthContext` 対応に**
10. **`teams.py` の招待メール送信統合**
11. **CLI** (`cli.py`)
12. **設定検証・環境変数整理**
13. **Admin UI**: AuthClient, Context, middleware
14. **Admin UI**: 認証ページ、Supabase 撤去
15. **テスト全件**
16. **ドキュメント更新**
17. **本番デプロイ準備**（環境変数設定、Fly secrets 整備）

各ステップで PR 単位で進める。テストは各ステップで通る状態を維持。

### 12.2 リスクと緩和

| リスク | 緩和策 |
|---|---|
| CORS 厳格化で既存タイル利用者が壊れる | TwoTierCORS でタイル系は permissive 維持 |
| Cookie SameSite=None でブラウザ差 | Chrome/Firefox/Safari の挙動を事前検証、HTTPS 必須確認 |
| `JWT_SECRET` 設定漏れ | 起動時バリデーションで fail-fast |
| 既存 `/api/auth/me` 利用箇所のリグレッション | 新ルーターに移設後も health.py で互換維持（リダイレクト or 同ハンドラ） |
| API キー使用ログの DB 書き込み負荷 | サンプリング率制御 + Phase 4 で非同期化 |
| プロバイダ間の挙動ドリフト | 共通契約テストで検出 |

### 12.3 ロールバック計画

各 PR を独立にロールバック可能に保つ。万が一プロバイダ実装に問題が見つかった場合:
- `AUTH_PROVIDER=supabase` に戻すだけで現行動作に復帰
- DB スキーマは加算のみ（既存テーブル変更なし）なのでロールバック不要

---

## 13. オープンクエスチョン・将来課題

### 13.1 Phase 3 で決定済み（再確認不要）

設計判断はすべて本仕様セクション 2 に記録。

### 13.2 Phase 4 以降の課題

- MFA（TOTP）
- OAuth ソーシャルログイン
- HTML メールテンプレート
- Have I Been Pwned 統合
- メール送信失敗時のリトライキュー
- 監査ログ UI
- Playwright によるフロントエンド E2E テスト
- Redis 経由の API キー使用ログ非同期書き込み
- ポータブル RLS（`current_setting('app.user_id')` 方式）
- Admin UI の SSR 化（現在は client-rendered）
- アカウント無効化・復活 UI
- 複数デバイスのセッション管理 UI

### 13.3 Phase 4 以降のインフラ移行課題

将来 Cloudflare 寄せ／Neon 移行を検討する際は、本設計が以下の状態を担保していることを前提とできる:
- 認証層は JWT 発行者非依存
- DB は Supabase 固有関数を使用しない
- Postgres さえ残せば認証はどこでも動く
- ストレージは S3 互換 API に統一可能

---

## 14. 関連ドキュメント

- `docs/INFRA_MIGRATION_INVESTIGATION.md` — Cloudflare 移行検討記録（本仕様の動機）
- `CLAUDE.md` — プロジェクトガイダンス（Supabase 依存方針が記載）
- `HANDOVER_S3.md` — Season 3 全体進捗
- `ROADMAP_S3.md` — Season 3 ロードマップ
- `api/README.md` / `app/README.md` — 既存実装の構造

---

## 15. 改訂履歴

| 日付 | 著者 | 変更内容 |
|---|---|---|
| 2026-05-08 | Claude（設計）/ otsuka（決定） | 初版作成。9 セクション全て承認後にスペック化 |
