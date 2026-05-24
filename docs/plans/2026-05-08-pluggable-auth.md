# プラガブル認証・認可（RBAC） 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** geo-base に Supabase 非依存のプラガブル認証バックエンドとチーム/ロールベースの認可機構を実装し、Admin UI も Supabase 抜きで動作するようにする。

**Architecture:** `AuthProvider` ABC を中心に local/supabase の 2 実装を提供し、起動時に環境変数で切替。共有ユーティリティ（jwt/password/tokens/rate_limit/email_backends）と AuthContext（JWT/API キー統一）を組み合わせる。タイル系は CORS 公開を維持し API キーで行レベル認可。

**Tech Stack:** Python 3.11 + FastAPI、psycopg2、PyJWT、passlib[bcrypt]、httpx、Next.js 16、TypeScript、PostgreSQL + PostGIS。

**Reference Spec:** `docs/specs/2026-05-08-pluggable-auth-design.md`（本計画はこのスペックの実装手順）

---

## ファイル構成（新規・変更対象）

### 新規作成（API）

```
api/lib/auth/                              # 新規パッケージ（既存 auth.py を置換）
├── __init__.py                            # 公開 API + factory
├── models.py                              # User, AuthResult, TokenPair
├── errors.py                              # AuthError 階層
├── provider.py                            # AuthProvider ABC
├── context.py                             # AuthContext
├── api_key_auth.py                        # API キー検証 + AuthContext 化
├── jwt_utils.py                           # JWT encode/decode
├── password.py                            # bcrypt + ポリシー
├── tokens.py                              # refresh token rotation
├── rate_limit.py                          # ログイン試行制限
├── cli.py                                 # python -m lib.auth.cli
├── providers/
│   ├── __init__.py
│   ├── local.py                           # LocalAuthProvider
│   └── supabase.py                        # SupabaseAuthProvider
└── email_backends/
    ├── __init__.py                        # EmailBackend ABC + factory
    ├── null_backend.py
    ├── console_backend.py
    ├── smtp_backend.py
    └── templates.py

api/lib/cors_middleware.py                 # 新規 TwoTierCORSMiddleware
api/lib/routers/auth.py                    # 新規 (10 endpoint)

docker/postgis-init/04_auth_schema.sql     # 新規（users/refresh_tokens/login_attempts/password_reset_tokens）
```

### 変更対象（API）

```
api/lib/auth.py                            # 削除（auth/ パッケージへ統合）
api/lib/config.py                          # 設定追加 + 起動時バリデーション
api/lib/main.py                            # CORS middleware 差し替え + auth_router 追加
api/lib/routers/health.py                  # /api/auth/me 削除
api/lib/routers/teams.py                   # 招待メール送信統合 + email 検証
api/lib/routers/tiles/dynamic.py           # AuthContext 対応
api/lib/routers/tiles/pmtiles.py           # 同上
api/lib/routers/tiles/raster.py            # 同上
api/lib/routers/tiles/mbtiles.py           # 同上
api/lib/routers/tilesets.py                # tilejson endpoint で AuthContext 対応
api/pyproject.toml                         # passlib, respx, freezegun 追加

docker/postgis-init/04_rls_policies.sql    # → 09_rls_policies.sql にリネーム
docker/postgis-init/04_rls_policies.sql.supabase  # → 09_rls_policies.sql.supabase にリネーム
```

### 新規作成（API テスト）

```
api/tests/test_auth/__init__.py
api/tests/test_auth/test_jwt_utils.py
api/tests/test_auth/test_password.py
api/tests/test_auth/test_tokens.py
api/tests/test_auth/test_rate_limit.py
api/tests/test_auth/test_email_backends.py
api/tests/test_auth/test_email_templates.py
api/tests/test_auth/test_models.py
api/tests/test_auth/test_errors.py
api/tests/test_auth/test_local_provider.py
api/tests/test_auth/test_supabase_provider.py
api/tests/test_auth/test_context.py
api/tests/test_auth/test_api_key_auth.py
api/tests/test_auth/test_factory.py
api/tests/test_auth/test_cli.py
api/tests/test_auth/test_cors_middleware.py
api/tests/test_routers/__init__.py
api/tests/test_routers/test_auth_routes.py
api/tests/test_routers/test_tile_access.py
api/tests/test_integration/__init__.py
api/tests/test_integration/test_login_flow.py
api/tests/test_integration/test_invitation_flow.py
api/tests/test_integration/test_password_reset_flow.py
api/tests/test_integration/test_team_access.py
api/tests/test_provider_contract.py
```

### 変更対象（API テスト）

```
api/tests/conftest.py                      # 新規フィクスチャ追加
api/tests/test_teams.py                    # 招待メール送信テスト追加
api/tests/test_api_keys.py                 # （変更最小）
```

### 新規作成（Admin UI）

```
app/src/middleware.ts
app/src/lib/auth/client.ts
app/src/lib/auth/context.tsx
app/src/lib/auth/types.ts
app/src/lib/auth/errors.ts
app/src/app/accept-invitation/page.tsx
app/src/app/password-reset/request/page.tsx
app/src/app/password-reset/confirm/page.tsx
app/src/app/settings/profile/page.tsx
app/src/app/settings/password/page.tsx
app/src/components/auth/login-form.tsx
app/src/components/auth/invitation-signup-form.tsx
app/src/components/auth/password-reset-form.tsx
```

### 変更対象（Admin UI）

```
app/src/app/layout.tsx                     # AuthProvider でラップ
app/src/app/login/page.tsx                 # Supabase クライアント削除、自前 AuthClient へ
app/src/lib/api.ts                         # Authorization 自動付与 + 401 retry
app/next.config.js                         # 開発時 API rewrite
app/package.json                           # @supabase/* 削除
app/.env.example                           # Supabase 関連削除
```

### 削除対象（Admin UI）

```
app/src/lib/supabase/                      # ディレクトリ丸ごと削除
```

### 新規作成（ドキュメント）

```
docs/AUTH_SETUP.md
docs/AUTH_MIGRATION.md
api/.env.example                           # 全項目を明示（既存ない場合）
```

### 変更対象（ドキュメント）

```
LOCAL_DEVELOPMENT.md
api/README.md
app/README.md
CLAUDE.md
HANDOVER_S3.md
docs/INFRA_MIGRATION_INVESTIGATION.md
```

---

## タスク分解の方針

- **Phase ごとに独立してテスト可能**（あるフェーズが終われば次に進める）
- **TDD サイクル**: 各タスクで「テスト書く → 失敗確認 → 実装 → 成功確認 → コミット」
- **コミット粒度**: タスク単位またはサブタスク単位（独立リバート可能）
- **既存 API 互換**: 既存ルーター（teams.py など）への影響を最小化、`require_auth` シグネチャ維持

---

## Phase 0: プロジェクト準備

### Task 0.1: 開発依存関係の追加

**Files:**
- Modify: `api/pyproject.toml`

- [ ] **Step 1: 現状確認**

```bash
cd api && grep -E "passlib|respx|freezegun" pyproject.toml || echo "Need to add"
```

- [ ] **Step 2: `pyproject.toml` を編集**

`api/pyproject.toml` の `dependencies` に追加:

```toml
"passlib[bcrypt]>=1.7.4",
```

`[project.optional-dependencies]` の `dev` に追加:

```toml
"respx>=0.21.0",
"freezegun>=1.4.0",
```

- [ ] **Step 3: 依存解決**

```bash
cd api && uv sync --extra dev
```

期待: 新パッケージがインストールされる。

- [ ] **Step 4: 動作確認**

```bash
cd api && uv run python -c "import passlib.hash; import respx; import freezegun; print('OK')"
```

期待: `OK`

- [ ] **Step 5: コミット**

```bash
git add api/pyproject.toml api/uv.lock
git commit -m "chore(api): add passlib, respx, freezegun for auth implementation"
```

### Task 0.2: スキーマファイルの番号体系整理

**Files:**
- Rename: `docker/postgis-init/04_rls_policies.sql` → `09_rls_policies.sql`
- Rename: `docker/postgis-init/04_rls_policies.sql.supabase` → `09_rls_policies.sql.supabase`

- [ ] **Step 1: リネーム実行**

```bash
cd docker/postgis-init
git mv 04_rls_policies.sql 09_rls_policies.sql
git mv 04_rls_policies.sql.supabase 09_rls_policies.sql.supabase
```

- [ ] **Step 2: 確認**

```bash
ls docker/postgis-init/
```

期待: `04_*` の RLS ファイルが消え、`09_*` で表示される。

- [ ] **Step 3: コミット**

```bash
git commit -m "chore(db): rename RLS schema files from 04 to 09 to make room for auth schema"
```

### Task 0.3: `04_auth_schema.sql` の作成

**Files:**
- Create: `docker/postgis-init/04_auth_schema.sql`

- [ ] **Step 1: ファイル作成**

スペック §4.1 のスキーマを実装。`docker/postgis-init/04_auth_schema.sql`:

```sql
-- =============================================================================
-- geo-base Authentication Schema (Phase 3 / Step 3.3-A)
-- =============================================================================
-- 認証関連テーブル。AUTH_PROVIDER=local 時に使用される。
-- supabase モードでは users テーブルは空のまま、auth.users が代替。
-- Run after 01_init.sql (uses update_updated_at_column())
-- =============================================================================

-- USERS（local モード用ユーザーストア）
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified_at TIMESTAMPTZ,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'authenticated',
    is_active BOOLEAN DEFAULT TRUE,
    app_metadata JSONB DEFAULT '{}',
    user_metadata JSONB DEFAULT '{}',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT email_lowercase CHECK (email = LOWER(email))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active) WHERE is_active = true;

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE users IS 'ユーザーアカウント（local モード時のみ使用、supabase モード時は auth.users を参照）';

-- REFRESH TOKENS
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    user_agent VARCHAR(500),
    ip_address INET,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(255),
    replaced_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);

COMMENT ON TABLE refresh_tokens IS 'リフレッシュトークン（rotation + 盗難検知）';

-- LOGIN ATTEMPTS（レート制限用）
CREATE TABLE IF NOT EXISTS auth_login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255),
    ip_address INET,
    success BOOLEAN NOT NULL,
    user_agent VARCHAR(500),
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_email_time ON auth_login_attempts (email, attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_ip_time ON auth_login_attempts (ip_address, attempted_at DESC);

COMMENT ON TABLE auth_login_attempts IS 'ログイン試行履歴（5回失敗/15分でロック）';

-- PASSWORD RESET TOKENS
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    ip_address INET
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens (expires_at);

COMMENT ON TABLE password_reset_tokens IS 'パスワードリセットトークン（1時間有効、1回使用）';

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cleanup_old_login_attempts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_login_attempts
    WHERE attempted_at < NOW() - INTERVAL '24 hours';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION count_recent_failed_logins(
    p_email VARCHAR(255),
    p_window_minutes INTEGER DEFAULT 15
)
RETURNS INTEGER AS $$
DECLARE
    fail_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO fail_count
    FROM auth_login_attempts
    WHERE email = LOWER(p_email)
      AND success = FALSE
      AND attempted_at > NOW() - (p_window_minutes || ' minutes')::INTERVAL;
    RETURN fail_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cleanup_expired_password_reset_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM password_reset_tokens
    WHERE expires_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

- [ ] **Step 2: スキーマ再構築（ローカル）**

```bash
cd docker
docker compose down -v
docker compose up -d
sleep 10
docker compose exec postgis psql -U postgres -d geo_base -c "\dt"
```

期待: `users`, `refresh_tokens`, `auth_login_attempts`, `password_reset_tokens` を含むテーブル一覧が表示される。

- [ ] **Step 3: テーブル詳細確認**

```bash
docker compose exec postgis psql -U postgres -d geo_base -c "\d users"
docker compose exec postgis psql -U postgres -d geo_base -c "\d refresh_tokens"
```

期待: スキーマ通りのカラムが定義されている。

- [ ] **Step 4: コミット**

```bash
git add docker/postgis-init/04_auth_schema.sql
git commit -m "feat(db): add auth schema (users, refresh_tokens, auth_login_attempts, password_reset_tokens)"
```

---

## Phase 1: 基盤ユーティリティ

このフェーズで作る部品は他に依存しない（または既存のみ）。各ファイルは TDD で実装。

### Task 1.1: `errors.py` (auth エラー階層)

**Files:**
- Create: `api/lib/auth/errors.py`
- Create: `api/lib/auth/__init__.py` (空ファイルでも作成 = パッケージ化)
- Create: `api/tests/test_auth/__init__.py`
- Create: `api/tests/test_auth/test_errors.py`

注意: 既存 `api/lib/auth.py` は **Task 2.5 でパッケージへ完全移行する**まで残す。Phase 1 では `api/lib/auth/` パッケージ作成 + `api/lib/auth.py` 共存を許容する。Pythonは同一名のファイルとパッケージ共存時にパッケージを優先するが、Task 2.5 で完全移行するため一時的な状態と考える。

実は安全のため、Phase 1 の最初は **新規モジュールを `api/lib/_auth_v2/`** などの別名で作成し、Task 2.5 で `_auth_v2/` → `auth/` リネーム + 旧 `auth.py` 削除が確実。

**改訂方針**: Phase 1〜2 の全モジュールは **`api/lib/_auth_pkg/`** という一時ディレクトリに作成し、Task 2.5 で `_auth_pkg/` → `auth/`（旧 `auth.py` を削除した上で）にリネームする。これによりインクリメンタル開発中に既存 `from lib.auth import User` が壊れない。

**以降の Phase 1〜2 タスクの "Files" 表記は `api/lib/_auth_pkg/...` だが、Task 2.5 でリネーム済みとして以後 `api/lib/auth/...` で参照する。**

- [ ] **Step 1: `_auth_pkg/__init__.py` を作成（空）**

```bash
mkdir -p api/lib/_auth_pkg
touch api/lib/_auth_pkg/__init__.py
mkdir -p api/tests/test_auth
touch api/tests/test_auth/__init__.py
```

- [ ] **Step 2: テスト作成**

`api/tests/test_auth/test_errors.py`:

```python
"""Tests for auth.errors module."""
import pytest
from lib._auth_pkg.errors import (
    AuthError,
    InvalidCredentials,
    RateLimited,
    UserNotFound,
    UserAlreadyExists,
    InvalidToken,
    WeakPassword,
    ProviderError,
)


class TestAuthErrorHierarchy:
    def test_all_subclass_auth_error(self):
        for cls in [InvalidCredentials, RateLimited, UserNotFound,
                    UserAlreadyExists, InvalidToken, WeakPassword, ProviderError]:
            assert issubclass(cls, AuthError)
            assert issubclass(cls, Exception)

    def test_can_raise_with_message(self):
        with pytest.raises(InvalidCredentials, match="bad creds"):
            raise InvalidCredentials("bad creds")

    def test_can_catch_via_base_class(self):
        with pytest.raises(AuthError):
            raise RateLimited("locked out")
```

- [ ] **Step 3: テストを実行して失敗を確認**

```bash
cd api && uv run pytest tests/test_auth/test_errors.py -v
```

期待: `ModuleNotFoundError: No module named 'lib._auth_pkg.errors'`

- [ ] **Step 4: 実装作成**

`api/lib/_auth_pkg/errors.py`:

```python
"""認証関連エラー階層。すべて AuthError を継承する。"""


class AuthError(Exception):
    """認証エラーの基底クラス。"""


class InvalidCredentials(AuthError):
    """email/password 不一致、または検証不可能なトークン。"""


class RateLimited(AuthError):
    """ログイン失敗回数が閾値を超過。"""


class UserNotFound(AuthError):
    """指定されたユーザーが存在しない。"""


class UserAlreadyExists(AuthError):
    """既に同じ email でアカウントが存在する。"""


class InvalidToken(AuthError):
    """JWT/refresh/reset トークンが無効・期限切れ・revoked。"""


class WeakPassword(AuthError):
    """パスワードがポリシーを満たさない。"""


class ProviderError(AuthError):
    """上流プロバイダ（Supabase API 等）のエラー。"""
```

- [ ] **Step 5: テスト成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_errors.py -v
```

期待: 3 テストが PASS。

- [ ] **Step 6: コミット**

```bash
git add api/lib/_auth_pkg/__init__.py api/lib/_auth_pkg/errors.py \
        api/tests/test_auth/__init__.py api/tests/test_auth/test_errors.py
git commit -m "feat(auth): add AuthError hierarchy"
```

### Task 1.2: `models.py` (User, AuthResult, TokenPair)

**Files:**
- Create: `api/lib/_auth_pkg/models.py`
- Create: `api/tests/test_auth/test_models.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_models.py`:

```python
"""Tests for auth.models module."""
import pytest
from pydantic import ValidationError
from lib._auth_pkg.models import User, AuthResult, TokenPair


class TestUser:
    def test_minimal_construction(self):
        u = User(id="abc-123")
        assert u.id == "abc-123"
        assert u.email is None
        assert u.email_verified is False

    def test_full_construction(self):
        u = User(id="abc", email="x@y.com", role="authenticated",
                 name="Alice", email_verified=True,
                 app_metadata={"provider": "local"})
        assert u.email == "x@y.com"
        assert u.app_metadata == {"provider": "local"}


class TestAuthResult:
    def test_authenticated(self):
        u = User(id="abc")
        r = AuthResult(is_authenticated=True, user=u)
        assert r.is_authenticated is True
        assert r.user.id == "abc"
        assert r.error is None

    def test_failed(self):
        r = AuthResult(is_authenticated=False, error="expired")
        assert r.is_authenticated is False
        assert r.user is None
        assert r.error == "expired"


class TestTokenPair:
    def test_basic(self):
        t = TokenPair(access_token="at", refresh_token="rt", expires_in=900)
        assert t.access_token == "at"
        assert t.token_type == "Bearer"
        assert t.expires_in == 900

    def test_requires_fields(self):
        with pytest.raises(ValidationError):
            TokenPair(access_token="at")  # missing refresh_token, expires_in
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_models.py -v
```

期待: ImportError

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/models.py`:

```python
"""共通モデル定義。プロバイダ非依存。"""
from typing import Optional, Any
from pydantic import BaseModel


class User(BaseModel):
    """認証済みユーザーモデル。"""
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    app_metadata: Optional[dict[str, Any]] = None
    user_metadata: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    email_verified: bool = False


class AuthResult(BaseModel):
    """JWT 検証結果。"""
    is_authenticated: bool
    user: Optional[User] = None
    error: Optional[str] = None


class TokenPair(BaseModel):
    """ログイン/リフレッシュ時のトークンレスポンス。"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_models.py -v
```

期待: 6 テスト PASS

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/models.py api/tests/test_auth/test_models.py
git commit -m "feat(auth): add User, AuthResult, TokenPair models"
```

### Task 1.3: `jwt_utils.py` (JWT encode/decode)

**Files:**
- Create: `api/lib/_auth_pkg/jwt_utils.py`
- Create: `api/tests/test_auth/test_jwt_utils.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_jwt_utils.py`:

```python
"""Tests for auth.jwt_utils module."""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from lib._auth_pkg.jwt_utils import (
    issue_access_token,
    decode_access_token,
    claims_to_user,
)
from lib._auth_pkg.models import User
from lib._auth_pkg.errors import InvalidToken


SECRET = "test-secret-do-not-use-in-prod-" + "x" * 40
AUD = "authenticated"
ISS = "geo-base-test"


class TestIssueAccessToken:
    def test_returns_string(self):
        u = User(id="abc-123", email="a@b.com", role="authenticated")
        token = issue_access_token(u, secret=SECRET, audience=AUD, issuer=ISS)
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT 形式

    def test_includes_standard_claims(self):
        u = User(id="abc", email="a@b.com", role="authenticated")
        token = issue_access_token(u, secret=SECRET, audience=AUD, issuer=ISS, ttl_seconds=900)
        decoded = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience=AUD)
        assert decoded["sub"] == "abc"
        assert decoded["email"] == "a@b.com"
        assert decoded["role"] == "authenticated"
        assert decoded["iss"] == ISS
        assert decoded["aud"] == AUD
        assert "iat" in decoded
        assert "exp" in decoded

    def test_ttl_applied(self):
        u = User(id="abc")
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_access_token(u, secret=SECRET, audience=AUD, ttl_seconds=900)
            decoded = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience=AUD)
            assert decoded["exp"] - decoded["iat"] == 900


class TestDecodeAccessToken:
    def test_valid_token(self):
        u = User(id="abc", email="a@b.com")
        token = issue_access_token(u, secret=SECRET, audience=AUD)
        claims = decode_access_token(token, secret=SECRET, audience=AUD)
        assert claims["sub"] == "abc"
        assert claims["email"] == "a@b.com"

    def test_invalid_signature_raises(self):
        u = User(id="abc")
        token = issue_access_token(u, secret=SECRET, audience=AUD)
        with pytest.raises(InvalidToken):
            decode_access_token(token, secret="wrong-secret", audience=AUD)

    def test_wrong_audience_raises(self):
        u = User(id="abc")
        token = issue_access_token(u, secret=SECRET, audience="aud1")
        with pytest.raises(InvalidToken):
            decode_access_token(token, secret=SECRET, audience="aud2")

    def test_expired_raises(self):
        u = User(id="abc")
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_access_token(u, secret=SECRET, audience=AUD, ttl_seconds=60)
        with freeze_time("2026-01-01 00:02:00"):
            with pytest.raises(InvalidToken):
                decode_access_token(token, secret=SECRET, audience=AUD)

    def test_malformed_raises(self):
        with pytest.raises(InvalidToken):
            decode_access_token("not-a-jwt", secret=SECRET, audience=AUD)

    def test_none_alg_attack_rejected(self):
        # JWT 'none' algorithm 攻撃を拒否
        payload = {"sub": "abc", "aud": AUD}
        evil = pyjwt.encode(payload, "", algorithm="none")
        with pytest.raises(InvalidToken):
            decode_access_token(evil, secret=SECRET, audience=AUD)


class TestClaimsToUser:
    def test_basic(self):
        claims = {"sub": "abc", "email": "a@b.com", "role": "authenticated"}
        u = claims_to_user(claims)
        assert u.id == "abc"
        assert u.email == "a@b.com"
        assert u.role == "authenticated"

    def test_includes_metadata(self):
        claims = {
            "sub": "abc",
            "app_metadata": {"provider": "local"},
            "user_metadata": {"name": "Alice"},
        }
        u = claims_to_user(claims)
        assert u.app_metadata == {"provider": "local"}
        assert u.user_metadata == {"name": "Alice"}
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_jwt_utils.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/jwt_utils.py`:

```python
"""JWT エンコード・デコード。署名鍵・audience は引数指定。

このモジュールは純粋関数のみで、設定取得は呼び出し側の責任。
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidSignatureError,
    DecodeError,
    InvalidAlgorithmError,
)

from .errors import InvalidToken
from .models import User


ALGORITHM = "HS256"


def issue_access_token(
    user: User,
    *,
    secret: str,
    audience: str,
    issuer: str = "geo-base",
    ttl_seconds: int = 900,
) -> str:
    """HS256 で標準クレーム（sub/email/role/aud/iss/iat/exp）の JWT を発行する。"""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user.id,
        "aud": audience,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    if user.email is not None:
        payload["email"] = user.email
    if user.role is not None:
        payload["role"] = user.role
    if user.app_metadata is not None:
        payload["app_metadata"] = user.app_metadata
    if user.user_metadata is not None:
        payload["user_metadata"] = user.user_metadata

    return pyjwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, *, secret: str, audience: str) -> dict[str, Any]:
    """JWT を検証し、クレーム dict を返す。検証失敗時は InvalidToken を raise。"""
    try:
        return pyjwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=audience,
            options={"require": ["exp", "iat", "sub", "aud"]},
        )
    except ExpiredSignatureError:
        raise InvalidToken("Token has expired")
    except InvalidAudienceError:
        raise InvalidToken("Invalid token audience")
    except (InvalidSignatureError, DecodeError, InvalidAlgorithmError) as e:
        raise InvalidToken(f"Invalid token: {e}")
    except InvalidTokenError as e:
        raise InvalidToken(f"Invalid token: {e}")


def claims_to_user(claims: dict[str, Any]) -> User:
    """JWT クレーム dict を User モデルに変換。"""
    return User(
        id=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role"),
        app_metadata=claims.get("app_metadata"),
        user_metadata=claims.get("user_metadata"),
    )
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_jwt_utils.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/jwt_utils.py api/tests/test_auth/test_jwt_utils.py
git commit -m "feat(auth): add jwt_utils for HS256 encode/decode with audience validation"
```

### Task 1.4: `password.py` (bcrypt + ポリシー)

**Files:**
- Create: `api/lib/_auth_pkg/password.py`
- Create: `api/tests/test_auth/test_password.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_password.py`:

```python
"""Tests for auth.password module."""
import pytest
from lib._auth_pkg.password import (
    hash_password,
    verify_password,
    check_password_policy,
    MIN_PASSWORD_LENGTH,
)
from lib._auth_pkg.errors import WeakPassword


class TestHashPassword:
    def test_returns_string(self):
        h = hash_password("ValidPass123")
        assert isinstance(h, str)
        assert len(h) > 50  # bcrypt ハッシュは 60 文字程度

    def test_different_calls_produce_different_hashes(self):
        # bcrypt は salt を含むため毎回違うハッシュになる
        h1 = hash_password("Same1234")
        h2 = hash_password("Same1234")
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password(self):
        h = hash_password("MyPass123")
        assert verify_password("MyPass123", h) is True

    def test_wrong_password(self):
        h = hash_password("MyPass123")
        assert verify_password("WrongPass", h) is False

    def test_invalid_hash_returns_false(self):
        # 不正なハッシュ文字列でも例外を出さず False を返す
        assert verify_password("anything", "not-a-bcrypt-hash") is False


class TestCheckPasswordPolicy:
    def test_valid_password(self):
        check_password_policy("ValidPass123")  # 例外なし

    def test_too_short(self):
        with pytest.raises(WeakPassword, match=str(MIN_PASSWORD_LENGTH)):
            check_password_policy("Short1")

    def test_letters_only(self):
        with pytest.raises(WeakPassword):
            check_password_policy("OnlyLetters")

    def test_digits_only(self):
        with pytest.raises(WeakPassword):
            check_password_policy("12345678")

    def test_letter_with_symbol_ok(self):
        check_password_policy("Hello!@#$")  # 英字 + 記号

    def test_letter_with_digit_ok(self):
        check_password_policy("Hello123")

    def test_no_max_length(self):
        # 最大長制限はない（NIST 推奨）
        check_password_policy("a" * 200 + "1")
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_password.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/password.py`:

```python
"""パスワードのハッシュ化・検証・ポリシーチェック。

bcrypt（passlib 経由）使用。NIST SP 800-63B 準拠で過度な複雑性は要求しない。
"""
from passlib.hash import bcrypt

from .errors import WeakPassword


MIN_PASSWORD_LENGTH = 8
BCRYPT_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    """bcrypt でパスワードをハッシュ化。salt は自動生成される。"""
    return bcrypt.using(rounds=BCRYPT_ROUNDS).hash(plaintext)


def verify_password(plaintext: str, hash_str: str) -> bool:
    """定時間比較でパスワードを検証。不正なハッシュ文字列でも例外を出さず False。"""
    try:
        return bcrypt.verify(plaintext, hash_str)
    except (ValueError, TypeError):
        return False


def check_password_policy(plaintext: str) -> None:
    """パスワードポリシー検証。違反時は WeakPassword を raise。

    ポリシー:
    - 最小 8 文字
    - 英字を 1 つ以上含む
    - 数字または記号を 1 つ以上含む
    """
    if len(plaintext) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )

    has_letter = any(c.isalpha() for c in plaintext)
    has_digit_or_symbol = any(c.isdigit() or not c.isalnum() for c in plaintext)

    if not has_letter:
        raise WeakPassword("Password must contain at least one letter")
    if not has_digit_or_symbol:
        raise WeakPassword("Password must contain at least one digit or symbol")
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_password.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/password.py api/tests/test_auth/test_password.py
git commit -m "feat(auth): add password hashing (bcrypt) and policy check"
```

---

**[Phase 1 続き → Task 1.5 以降は次の書き出しで継続]**

### Task 1.5: `tokens.py` (refresh token rotation + 盗難検知)

**Files:**
- Create: `api/lib/_auth_pkg/tokens.py`
- Create: `api/tests/test_auth/test_tokens.py`
- Modify: `api/tests/conftest.py`（DB 接続フィクスチャを参照可能にする）

このタスクは DB 接続が必要。既存 `conftest.py` を確認し、`db_conn` フィクスチャがあれば流用、なければ追加する。

- [ ] **Step 1: 既存 conftest.py 確認**

```bash
cd api && grep -n "db_conn\|fixture" tests/conftest.py | head -30
```

期待: `db_conn` フィクスチャの存在を確認。なければ次ステップで追加。

- [ ] **Step 2: conftest.py に DB フィクスチャ追加（既存にない場合）**

`api/tests/conftest.py` の末尾に追加（既存 `db_conn` があればスキップ）:

```python
import os
import pytest
import psycopg2

@pytest.fixture
def db_conn():
    """テスト用 DB 接続。各テスト後に rollback。"""
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/geo_base")
    )
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def clean_auth_tables(db_conn):
    """auth 関連テーブルをクリーンアップ"""
    with db_conn.cursor() as cur:
        cur.execute("TRUNCATE refresh_tokens, auth_login_attempts, password_reset_tokens, users CASCADE")
    db_conn.commit()
    yield
```

- [ ] **Step 3: テスト作成**

`api/tests/test_auth/test_tokens.py`:

```python
"""Tests for auth.tokens module - refresh token rotation + reuse detection."""
import uuid
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from lib._auth_pkg.tokens import (
    issue_refresh_token,
    verify_and_rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    cleanup_expired_tokens,
    REFRESH_TOKEN_TTL_DAYS,
)
from lib._auth_pkg.errors import InvalidToken


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


class TestIssueRefreshToken:
    def test_returns_string_token(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id, ip="127.0.0.1", user_agent="pytest")
        assert isinstance(token, str)
        assert len(token) > 32  # urlsafe(48) は ~64 文字

    def test_stored_as_hash(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        with db_conn.cursor() as cur:
            cur.execute("SELECT token_hash, user_id FROM refresh_tokens WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            assert row[0] == _hash(token)
            assert str(row[1]) == user_id

    def test_each_token_unique(self, db_conn, clean_auth_tables, user_id):
        t1 = issue_refresh_token(db_conn, user_id)
        t2 = issue_refresh_token(db_conn, user_id)
        assert t1 != t2


class TestVerifyAndRotate:
    def test_valid_rotation(self, db_conn, clean_auth_tables, user_id):
        original = issue_refresh_token(db_conn, user_id)
        returned_user_id, new_token = verify_and_rotate_refresh_token(db_conn, original)
        assert returned_user_id == user_id
        assert new_token != original
        # 旧トークンが revoked
        with db_conn.cursor() as cur:
            cur.execute("SELECT revoked_at, replaced_by FROM refresh_tokens WHERE token_hash = %s", (_hash(original),))
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] is not None

    def test_invalid_token_raises(self, db_conn, clean_auth_tables):
        with pytest.raises(InvalidToken):
            verify_and_rotate_refresh_token(db_conn, "nonexistent-token")

    def test_reuse_detection_revokes_all(self, db_conn, clean_auth_tables, user_id):
        # 2 つトークンを発行、1 つを使用→ローテート、その後旧トークンを再提示
        t1 = issue_refresh_token(db_conn, user_id)
        t2 = issue_refresh_token(db_conn, user_id)
        _, _ = verify_and_rotate_refresh_token(db_conn, t1)  # t1 は revoked になる
        # 再利用 → 全失効
        with pytest.raises(InvalidToken):
            verify_and_rotate_refresh_token(db_conn, t1)
        # t2 も revoked になっているはず
        with db_conn.cursor() as cur:
            cur.execute("SELECT revoked_at, revoked_reason FROM refresh_tokens WHERE token_hash = %s", (_hash(t2),))
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] == "theft_detected"

    def test_expired_token_raises(self, db_conn, clean_auth_tables, user_id):
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_refresh_token(db_conn, user_id)
        with freeze_time("2026-03-01 00:00:00"):  # 30 日以上経過
            with pytest.raises(InvalidToken):
                verify_and_rotate_refresh_token(db_conn, token)


class TestRevoke:
    def test_revoke_specific(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        revoke_refresh_token(db_conn, token, reason="logout")
        with db_conn.cursor() as cur:
            cur.execute("SELECT revoked_at, revoked_reason FROM refresh_tokens WHERE token_hash = %s", (_hash(token),))
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] == "logout"

    def test_revoke_idempotent(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        revoke_refresh_token(db_conn, token)
        revoke_refresh_token(db_conn, token)  # 二重に呼んでも例外なし

    def test_revoke_nonexistent_no_error(self, db_conn, clean_auth_tables):
        revoke_refresh_token(db_conn, "nonexistent")  # 例外なし

    def test_revoke_all_user_tokens(self, db_conn, clean_auth_tables, user_id):
        for _ in range(3):
            issue_refresh_token(db_conn, user_id)
        count = revoke_all_user_tokens(db_conn, user_id, reason="password_changed")
        assert count == 3
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s AND revoked_at IS NOT NULL", (user_id,))
            assert cur.fetchone()[0] == 3


class TestCleanup:
    def test_cleanup_expired(self, db_conn, clean_auth_tables, user_id):
        with freeze_time("2026-01-01 00:00:00"):
            issue_refresh_token(db_conn, user_id)
        with freeze_time("2026-04-01 00:00:00"):
            count = cleanup_expired_tokens(db_conn)
            assert count >= 1
```

- [ ] **Step 4: 失敗確認**

```bash
cd docker && docker compose up -d  # PostGIS が起動済みであること
cd ../api && uv run pytest tests/test_auth/test_tokens.py -v
```

- [ ] **Step 5: 実装**

`api/lib/_auth_pkg/tokens.py`:

```python
"""リフレッシュトークンのライフサイクル管理。

セキュリティ機能:
- トークンローテーション: 検証時に新トークン発行 + 旧トークン revoke
- 再利用検知: revoked 済みトークンが再提示されたら、そのユーザーの全トークンを失効
"""
import secrets
import hashlib
import logging
from typing import Optional, Tuple

from .errors import InvalidToken


logger = logging.getLogger(__name__)


REFRESH_TOKEN_TTL_DAYS = 30
TOKEN_BYTES = 48  # urlsafe(48) で約 64 文字


def _hash_token(token: str) -> str:
    """SHA-256 で token をハッシュ化。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_refresh_token(
    conn,
    user_id: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """新しい refresh token を発行し、ハッシュを DB に保存。平文を返す。"""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(token)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens 
                (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES 
                (%s, %s, %s, %s, NOW() + (%s || ' days')::INTERVAL)
            """,
            (user_id, token_hash, ip, user_agent, REFRESH_TOKEN_TTL_DAYS),
        )
    conn.commit()
    return token


def verify_and_rotate_refresh_token(
    conn,
    refresh_token: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, str]:
    """検証 → 旧トークン revoke → 新トークン発行（rotation）。

    Returns: (user_id, new_refresh_token)
    Raises: InvalidToken if not_found / revoked (盗難検知付き) / expired
    """
    token_hash = _hash_token(refresh_token)

    with conn.cursor() as cur:
        # FOR UPDATE で行ロック（並行 refresh の race 防止）
        cur.execute(
            """
            SELECT id, user_id, revoked_at, expires_at
            FROM refresh_tokens
            WHERE token_hash = %s
            FOR UPDATE
            """,
            (token_hash,),
        )
        row = cur.fetchone()

        if row is None:
            conn.rollback()
            raise InvalidToken("Token not found")

        token_id, user_id, revoked_at, expires_at = row

        # ★ 再利用検知
        if revoked_at is not None:
            logger.warning(
                "Refresh token reuse detected", extra={"user_id": str(user_id)}
            )
            cur.execute(
                """
                UPDATE refresh_tokens 
                SET revoked_at = NOW(), revoked_reason = %s
                WHERE user_id = %s AND revoked_at IS NULL
                """,
                ("theft_detected", user_id),
            )
            conn.commit()
            raise InvalidToken("Token has been revoked (reuse detected)")

        from datetime import datetime, timezone
        if expires_at < datetime.now(timezone.utc):
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW(), revoked_reason = 'expired' WHERE id = %s",
                (token_id,),
            )
            conn.commit()
            raise InvalidToken("Token expired")

        # 新トークン発行
        new_token = secrets.token_urlsafe(TOKEN_BYTES)
        new_token_hash = _hash_token(new_token)
        cur.execute(
            """
            INSERT INTO refresh_tokens 
                (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES 
                (%s, %s, %s, %s, NOW() + (%s || ' days')::INTERVAL)
            RETURNING id
            """,
            (user_id, new_token_hash, ip, user_agent, REFRESH_TOKEN_TTL_DAYS),
        )
        new_token_id = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = 'rotated', replaced_by = %s
            WHERE id = %s
            """,
            (new_token_id, token_id),
        )

    conn.commit()
    return str(user_id), new_token


def revoke_refresh_token(conn, refresh_token: str, reason: str = "logout") -> None:
    """指定トークンを revoke。冪等。"""
    token_hash = _hash_token(refresh_token)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = %s
            WHERE token_hash = %s AND revoked_at IS NULL
            """,
            (reason, token_hash),
        )
    conn.commit()


def revoke_all_user_tokens(conn, user_id: str, reason: str) -> int:
    """ユーザーの全 active refresh token を revoke。Returns: 失効した件数。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = %s
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (reason, user_id),
        )
        count = cur.rowcount
    conn.commit()
    return count


def cleanup_expired_tokens(conn) -> int:
    """期限切れトークンを物理削除。Returns: 削除件数。"""
    with conn.cursor() as cur:
        cur.execute("SELECT cleanup_expired_refresh_tokens()")
        count = cur.fetchone()[0]
    conn.commit()
    return count
```

- [ ] **Step 6: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_tokens.py -v
```

期待: 全テスト PASS

- [ ] **Step 7: コミット**

```bash
git add api/lib/_auth_pkg/tokens.py api/tests/test_auth/test_tokens.py api/tests/conftest.py
git commit -m "feat(auth): add refresh token rotation with theft detection"
```

### Task 1.6: `rate_limit.py` (ログイン試行制限)

**Files:**
- Create: `api/lib/_auth_pkg/rate_limit.py`
- Create: `api/tests/test_auth/test_rate_limit.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_rate_limit.py`:

```python
"""Tests for auth.rate_limit module."""
import pytest
from freezegun import freeze_time

from lib._auth_pkg.rate_limit import (
    check_login_rate_limit,
    record_login_attempt,
    cleanup_old_attempts,
    MAX_FAILED_ATTEMPTS,
    WINDOW_MINUTES,
)
from lib._auth_pkg.errors import RateLimited


class TestCheckLoginRateLimit:
    def test_no_attempts_passes(self, db_conn, clean_auth_tables):
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_under_threshold_passes(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            record_login_attempt(db_conn, email="x@example.com", success=False, ip="1.1.1.1")
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_at_threshold_raises(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email="x@example.com", success=False, ip="1.1.1.1")
        with pytest.raises(RateLimited):
            check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_success_does_not_count(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email="x@example.com", success=True, ip="1.1.1.1")
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_old_attempts_ignored(self, db_conn, clean_auth_tables):
        with freeze_time("2026-01-01 00:00:00"):
            for _ in range(MAX_FAILED_ATTEMPTS):
                record_login_attempt(db_conn, email="x@example.com", success=False, ip="1.1.1.1")
        with freeze_time("2026-01-01 01:00:00"):  # 1 時間後
            check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_ip_threshold_independently_triggers(self, db_conn, clean_auth_tables):
        # 別 email でも同じ IP から失敗を重ねるとロック
        for i in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email=f"user{i}@example.com", success=False, ip="1.1.1.1")
        with pytest.raises(RateLimited):
            check_login_rate_limit(db_conn, email="newuser@example.com", ip="1.1.1.1")


class TestRecordLoginAttempt:
    def test_records_email_lowercased(self, db_conn, clean_auth_tables):
        record_login_attempt(db_conn, email="UPPER@example.com", success=True, ip="1.1.1.1")
        with db_conn.cursor() as cur:
            cur.execute("SELECT email FROM auth_login_attempts")
            assert cur.fetchone()[0] == "upper@example.com"

    def test_includes_user_agent(self, db_conn, clean_auth_tables):
        record_login_attempt(db_conn, email="x@y.com", success=False, ip="1.1.1.1", user_agent="pytest/1.0")
        with db_conn.cursor() as cur:
            cur.execute("SELECT user_agent FROM auth_login_attempts")
            assert cur.fetchone()[0] == "pytest/1.0"


class TestCleanup:
    def test_cleanup_old(self, db_conn, clean_auth_tables):
        with freeze_time("2026-01-01 00:00:00"):
            record_login_attempt(db_conn, email="x@y.com", success=False)
        with freeze_time("2026-01-03 00:00:00"):  # 2 日後
            count = cleanup_old_attempts(db_conn)
            assert count >= 1
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_rate_limit.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/rate_limit.py`:

```python
"""ログイン試行カウントとレート制限判定。

email または IP の **どちらか** が閾値超過でロック。
"""
from typing import Optional

from .errors import RateLimited


MAX_FAILED_ATTEMPTS = 5
WINDOW_MINUTES = 15


def check_login_rate_limit(
    conn,
    *,
    email: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """直近 WINDOW_MINUTES 分間の失敗回数を確認し、閾値超過なら RateLimited を raise。"""
    if email is None and ip is None:
        return  # チェック対象なし

    email_lower = email.lower() if email else None

    with conn.cursor() as cur:
        # email チェック
        if email_lower is not None:
            cur.execute(
                """
                SELECT COUNT(*) FROM auth_login_attempts
                WHERE email = %s AND success = FALSE
                  AND attempted_at > NOW() - (%s || ' minutes')::INTERVAL
                """,
                (email_lower, WINDOW_MINUTES),
            )
            count = cur.fetchone()[0]
            if count >= MAX_FAILED_ATTEMPTS:
                raise RateLimited(
                    f"Too many failed attempts for this account. Retry in {WINDOW_MINUTES} minutes."
                )

        # IP チェック
        if ip is not None:
            cur.execute(
                """
                SELECT COUNT(*) FROM auth_login_attempts
                WHERE ip_address = %s AND success = FALSE
                  AND attempted_at > NOW() - (%s || ' minutes')::INTERVAL
                """,
                (ip, WINDOW_MINUTES),
            )
            count = cur.fetchone()[0]
            if count >= MAX_FAILED_ATTEMPTS:
                raise RateLimited(
                    f"Too many failed attempts from this IP. Retry in {WINDOW_MINUTES} minutes."
                )


def record_login_attempt(
    conn,
    *,
    email: str,
    success: bool,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """ログイン試行を記録。email は小文字正規化。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO auth_login_attempts (email, ip_address, success, user_agent)
            VALUES (%s, %s, %s, %s)
            """,
            (email.lower(), ip, success, user_agent),
        )
    conn.commit()


def cleanup_old_attempts(conn) -> int:
    """24 時間以上前の試行履歴を削除。Returns: 削除件数。"""
    with conn.cursor() as cur:
        cur.execute("SELECT cleanup_old_login_attempts()")
        count = cur.fetchone()[0]
    conn.commit()
    return count
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_rate_limit.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/rate_limit.py api/tests/test_auth/test_rate_limit.py
git commit -m "feat(auth): add login rate limiting (5 failures / 15 min)"
```

### Task 1.7: `email_backends/` パッケージ

**Files:**
- Create: `api/lib/_auth_pkg/email_backends/__init__.py`
- Create: `api/lib/_auth_pkg/email_backends/null_backend.py`
- Create: `api/lib/_auth_pkg/email_backends/console_backend.py`
- Create: `api/lib/_auth_pkg/email_backends/smtp_backend.py`
- Create: `api/lib/_auth_pkg/email_backends/templates.py`
- Create: `api/tests/test_auth/test_email_backends.py`
- Create: `api/tests/test_auth/test_email_templates.py`

このタスクは複数ファイルなので 2 サブタスクに分割。

#### Task 1.7a: バックエンド本体（Null/Console/SMTP + ABC + factory）

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_email_backends.py`:

```python
"""Tests for auth.email_backends."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from lib._auth_pkg.email_backends import (
    EmailBackend,
    NullEmailBackend,
    ConsoleEmailBackend,
    SMTPEmailBackend,
)


class TestNullBackend:
    @pytest.mark.asyncio
    async def test_records_messages(self):
        b = NullEmailBackend()
        await b.send("a@b.com", "Subject", "Body")
        assert len(b.sent) == 1
        assert b.sent[0] == {"to": "a@b.com", "subject": "Subject", "body": "Body"}

    @pytest.mark.asyncio
    async def test_clear_resets(self):
        b = NullEmailBackend()
        await b.send("a@b.com", "S", "B")
        b.clear()
        assert b.sent == []


class TestConsoleBackend:
    @pytest.mark.asyncio
    async def test_writes_to_stdout(self, capsys):
        b = ConsoleEmailBackend()
        await b.send("a@b.com", "Hello", "Body content")
        captured = capsys.readouterr()
        assert "a@b.com" in captured.out
        assert "Hello" in captured.out
        assert "Body content" in captured.out


class TestSMTPBackend:
    @pytest.mark.asyncio
    async def test_calls_smtp(self):
        with patch("lib._auth_pkg.email_backends.smtp_backend.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            b = SMTPEmailBackend(
                host="smtp.example.com", port=587,
                username="user", password="pass",
                from_addr="no-reply@example.com", use_tls=True,
            )
            await b.send("to@example.com", "Hi", "Body")

            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user", "pass")
            mock_server.send_message.assert_called_once()


class TestABCEnforcement:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            EmailBackend()
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_email_backends.py -v
```

- [ ] **Step 3: ABC + factory 実装**

`api/lib/_auth_pkg/email_backends/__init__.py`:

```python
"""メール送信バックエンド。Null/Console/SMTP の 3 実装。"""
from abc import ABC, abstractmethod
from functools import lru_cache


class EmailBackend(ABC):
    """メール送信の抽象インタフェース。"""

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None:
        """プレーンテキストメールを送信する。"""


def _get_settings():
    """設定取得（遅延 import で循環依存を回避）"""
    from lib.config import get_settings
    return get_settings()


@lru_cache(maxsize=1)
def get_email_backend() -> EmailBackend:
    """環境変数 EMAIL_BACKEND から実装を選択。"""
    settings = _get_settings()
    backend_name = settings.email_backend

    if backend_name == "null":
        return NullEmailBackend()
    elif backend_name == "console":
        return ConsoleEmailBackend()
    elif backend_name == "smtp":
        return SMTPEmailBackend(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
            use_tls=settings.smtp_use_tls,
        )
    raise ValueError(f"Unknown EMAIL_BACKEND: {backend_name}")


# 実装を re-export
from .null_backend import NullEmailBackend  # noqa: E402
from .console_backend import ConsoleEmailBackend  # noqa: E402
from .smtp_backend import SMTPEmailBackend  # noqa: E402

__all__ = [
    "EmailBackend",
    "NullEmailBackend",
    "ConsoleEmailBackend",
    "SMTPEmailBackend",
    "get_email_backend",
]
```

`api/lib/_auth_pkg/email_backends/null_backend.py`:

```python
"""テスト用バックエンド。送信せず内部リストに記録。"""
from . import EmailBackend


class NullEmailBackend(EmailBackend):
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})

    def clear(self) -> None:
        self.sent.clear()
```

`api/lib/_auth_pkg/email_backends/console_backend.py`:

```python
"""ローカル開発用バックエンド。標準出力 + logger.info に出力。"""
import logging
from . import EmailBackend


logger = logging.getLogger(__name__)


class ConsoleEmailBackend(EmailBackend):
    async def send(self, to: str, subject: str, body: str) -> None:
        message = (
            f"\n{'=' * 60}\n"
            f"📧 EMAIL (console backend)\n"
            f"{'-' * 60}\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"{'-' * 60}\n"
            f"{body}\n"
            f"{'=' * 60}\n"
        )
        print(message)
        logger.info("Email sent (console)", extra={"to": to, "subject": subject})
```

`api/lib/_auth_pkg/email_backends/smtp_backend.py`:

```python
"""本番用 SMTP バックエンド。標準ライブラリのみ使用。"""
import smtplib
from email.message import EmailMessage
from typing import Optional

from . import EmailBackend


class SMTPEmailBackend(EmailBackend):
    def __init__(
        self,
        host: str,
        port: int,
        from_addr: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.from_addr = from_addr
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.set_content(body)

        # asyncio で同期 SMTP を呼ぶ（短時間処理なのでイベントループ blocking 許容）
        with smtplib.SMTP(self.host, self.port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)
```

- [ ] **Step 4: pytest-asyncio 設定確認**

`api/pyproject.toml` の pytest 設定に asyncio_mode を追加（既存設定にない場合）:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
asyncio_mode = "auto"  # ← 追加（既存にあればスキップ）
filterwarnings = ["ignore::DeprecationWarning"]
```

- [ ] **Step 5: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_email_backends.py -v
```

- [ ] **Step 6: コミット**

```bash
git add api/lib/_auth_pkg/email_backends/ api/tests/test_auth/test_email_backends.py api/pyproject.toml
git commit -m "feat(auth): add email backends (Null/Console/SMTP)"
```

#### Task 1.7b: メールテンプレート

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_email_templates.py`:

```python
"""Tests for auth.email_backends.templates."""
from datetime import datetime, timezone
from lib._auth_pkg.email_backends.templates import (
    render_invitation_email,
    render_password_reset_email,
)


class TestInvitationTemplate:
    def test_returns_subject_and_body(self):
        subject, body = render_invitation_email(
            team_name="Acme Team",
            inviter_name="Alice",
            accept_url="https://example.com/accept?token=abc",
            expires_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
        assert "Acme Team" in subject
        assert "Alice" in body
        assert "https://example.com/accept?token=abc" in body
        assert "2026" in body  # 期限日が含まれる


class TestPasswordResetTemplate:
    def test_returns_subject_and_body(self):
        subject, body = render_password_reset_email(
            user_name="Alice",
            reset_url="https://example.com/reset?token=xyz",
            expires_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert "password" in subject.lower() or "パスワード" in subject
        assert "https://example.com/reset?token=xyz" in body

    def test_handles_no_user_name(self):
        subject, body = render_password_reset_email(
            user_name=None,
            reset_url="https://example.com/reset?token=xyz",
            expires_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
        assert "https://example.com/reset?token=xyz" in body
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_email_templates.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/email_backends/templates.py`:

```python
"""メールテンプレート。Phase 3 はプレーンテキストのみ。"""
from datetime import datetime
from typing import Optional, Tuple


def render_invitation_email(
    team_name: str,
    inviter_name: str,
    accept_url: str,
    expires_at: datetime,
) -> Tuple[str, str]:
    """招待メールの (subject, body) を返す。"""
    subject = f"[geo-base] チーム「{team_name}」への招待"
    body = (
        f"{inviter_name} さんから「{team_name}」への参加招待が届いています。\n"
        f"\n"
        f"以下のリンクをクリックしてアカウントを作成・参加してください:\n"
        f"{accept_url}\n"
        f"\n"
        f"このリンクは {expires_at.strftime('%Y-%m-%d %H:%M UTC')} まで有効です。\n"
        f"\n"
        f"-- \n"
        f"geo-base\n"
        f"このメールに心当たりがない場合は無視してください。\n"
    )
    return subject, body


def render_password_reset_email(
    user_name: Optional[str],
    reset_url: str,
    expires_at: datetime,
) -> Tuple[str, str]:
    """パスワードリセットメールの (subject, body) を返す。"""
    subject = "[geo-base] パスワードリセットのご案内"
    greeting = f"{user_name} さん" if user_name else "ユーザー"
    body = (
        f"{greeting}、\n"
        f"\n"
        f"アカウントのパスワードリセットが要求されました。\n"
        f"以下のリンクをクリックして新しいパスワードを設定してください:\n"
        f"{reset_url}\n"
        f"\n"
        f"このリンクは {expires_at.strftime('%Y-%m-%d %H:%M UTC')} まで有効です。\n"
        f"\n"
        f"心当たりがない場合は、このメールを無視してください。\n"
        f"アカウントは安全です。\n"
        f"\n"
        f"-- \n"
        f"geo-base\n"
    )
    return subject, body
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_email_templates.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/email_backends/templates.py api/tests/test_auth/test_email_templates.py
git commit -m "feat(auth): add invitation and password reset email templates"
```

---


## Phase 2: AuthProvider 抽象化とプロバイダ実装

### Task 2.1: `provider.py` (AuthProvider ABC)

**Files:**
- Create: `api/lib/_auth_pkg/provider.py`
- Create: `api/tests/test_auth/test_factory.py`（一部のみ、ABC が抽象であること）

- [ ] **Step 1: テスト作成（抽象性確認）**

`api/tests/test_auth/test_factory.py` に以下を追加（後で factory テストも同ファイルに追加するため）:

```python
"""Tests for AuthProvider ABC and factory."""
import pytest
from lib._auth_pkg.provider import AuthProvider


class TestAuthProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AuthProvider()
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_factory.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/provider.py`:

```python
"""AuthProvider ABC - プラガブル認証の抽象インタフェース。"""
from abc import ABC, abstractmethod
from typing import Optional

from .models import AuthResult, TokenPair, User


class AuthProvider(ABC):
    """認証プロバイダの抽象インタフェース。

    起動時に AUTH_PROVIDER 環境変数で 1 つだけ生成される。
    実装: SupabaseAuthProvider, LocalAuthProvider
    """

    # === トークン検証（毎リクエストで呼ばれる） ===
    @abstractmethod
    async def verify_access_token(self, token: str) -> AuthResult:
        """アクセストークンを検証する。"""

    # === ユーザー検索 ===
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID でユーザーを検索。存在しなければ None。"""

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """email でユーザーを検索。"""

    # === 認証フロー ===
    @abstractmethod
    async def authenticate(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """email/password でログインしトークンペアを返す。

        Raises:
            InvalidCredentials: 認証失敗
            RateLimited: 試行回数超過
        """

    @abstractmethod
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """リフレッシュトークンを使って新しいトークンペアを取得（rotation）。

        Raises:
            InvalidToken: 無効/期限切れ/revoked
        """

    @abstractmethod
    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """リフレッシュトークンを失効させる（ログアウト）。冪等。"""

    # === ユーザー作成・更新 ===
    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
        email_verified: bool = False,
        app_metadata: Optional[dict] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        """新規ユーザーを作成。

        Raises:
            UserAlreadyExists: email 重複
            WeakPassword: ポリシー違反
        """

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        """ユーザープロフィールを更新。"""

    @abstractmethod
    async def update_password(self, user_id: str, new_password: str) -> None:
        """パスワードを更新。全 refresh token を失効させる責任は呼び出し側。"""

    # === パスワードリセット ===
    @abstractmethod
    async def request_password_reset(
        self,
        email: str,
        ip: Optional[str] = None,
    ) -> None:
        """パスワードリセットを要求（メール送信）。

        ユーザー存在の有無に関わらず常に成功する（情報漏洩防止）。
        """

    @abstractmethod
    async def confirm_password_reset(
        self,
        token: str,
        new_password: str,
    ) -> User:
        """リセットトークンで新パスワード設定。

        Raises:
            InvalidToken: トークン不正
            WeakPassword: ポリシー違反
        """
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_factory.py::TestAuthProviderABC -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/provider.py api/tests/test_auth/test_factory.py
git commit -m "feat(auth): add AuthProvider ABC interface"
```

### Task 2.2: `LocalAuthProvider`

**Files:**
- Create: `api/lib/_auth_pkg/providers/__init__.py`（空）
- Create: `api/lib/_auth_pkg/providers/local.py`
- Create: `api/tests/test_auth/test_local_provider.py`

- [ ] **Step 1: providers パッケージ作成**

```bash
mkdir -p api/lib/_auth_pkg/providers
touch api/lib/_auth_pkg/providers/__init__.py
```

- [ ] **Step 2: テスト作成**

`api/tests/test_auth/test_local_provider.py`:

```python
"""Tests for LocalAuthProvider."""
import pytest
import secrets
from unittest.mock import AsyncMock, patch

from lib._auth_pkg.providers.local import LocalAuthProvider
from lib._auth_pkg.errors import (
    InvalidCredentials, RateLimited, UserAlreadyExists,
    InvalidToken, WeakPassword,
)
from lib._auth_pkg.email_backends import NullEmailBackend


@pytest.fixture
def email_backend(monkeypatch):
    backend = NullEmailBackend()
    from lib._auth_pkg import email_backends as eb
    monkeypatch.setattr(eb, "get_email_backend", lambda: backend)
    return backend


@pytest.fixture
def provider(monkeypatch):
    """テスト用 LocalAuthProvider"""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-" + "x" * 50)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("JWT_ISSUER", "geo-base-test")
    from lib.config import get_settings
    get_settings.cache_clear()
    return LocalAuthProvider()


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_creates_user(self, provider, db_conn, clean_auth_tables):
        u = await provider.create_user("alice@example.com", "ValidPass123", name="Alice")
        assert u.id is not None
        assert u.email == "alice@example.com"
        assert u.name == "Alice"

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("alice@example.com", "ValidPass123")
        with pytest.raises(UserAlreadyExists):
            await provider.create_user("alice@example.com", "AnotherPass456")

    @pytest.mark.asyncio
    async def test_weak_password_raises(self, provider, db_conn, clean_auth_tables):
        with pytest.raises(WeakPassword):
            await provider.create_user("a@b.com", "short")

    @pytest.mark.asyncio
    async def test_email_lowercased(self, provider, db_conn, clean_auth_tables):
        u = await provider.create_user("UPPER@example.com", "ValidPass123")
        assert u.email == "upper@example.com"


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_correct_credentials(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        assert pair.access_token
        assert pair.refresh_token
        assert pair.expires_in == 900

    @pytest.mark.asyncio
    async def test_wrong_password(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "WrongPass", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_nonexistent_user_same_error(self, provider, db_conn, clean_auth_tables):
        # 存在しないユーザーでも InvalidCredentials（不存在を漏らさない）
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("nobody@example.com", "AnyPass", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_rate_limit_after_failures(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        for _ in range(5):
            with pytest.raises(InvalidCredentials):
                await provider.authenticate("a@b.com", "Wrong", ip="1.1.1.1")
        with pytest.raises(RateLimited):
            await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")


class TestVerifyAccessToken:
    @pytest.mark.asyncio
    async def test_valid_token(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        result = await provider.verify_access_token(pair.access_token)
        assert result.is_authenticated
        assert result.user.email == "a@b.com"

    @pytest.mark.asyncio
    async def test_invalid_token(self, provider):
        result = await provider.verify_access_token("not-a-jwt")
        assert not result.is_authenticated


class TestRefreshTokens:
    @pytest.mark.asyncio
    async def test_rotation(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        new_pair = await provider.refresh_tokens(pair.refresh_token, ip="1.1.1.1")
        assert new_pair.refresh_token != pair.refresh_token
        # 旧 refresh は使えない（盗難検知 → 全失効）
        with pytest.raises(InvalidToken):
            await provider.refresh_tokens(pair.refresh_token)


class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_request_sends_email(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        await provider.request_password_reset("a@b.com")
        assert len(email_backend.sent) == 1
        assert "a@b.com" == email_backend.sent[0]["to"]

    @pytest.mark.asyncio
    async def test_request_nonexistent_silent(self, provider, email_backend, db_conn, clean_auth_tables):
        # 存在しない email でも例外なく成功（情報漏洩防止）
        await provider.request_password_reset("nobody@example.com")
        assert len(email_backend.sent) == 0  # メールは送られない

    @pytest.mark.asyncio
    async def test_confirm_changes_password(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "OldPass123")
        await provider.request_password_reset("a@b.com")
        # メール本文からトークンを抽出（実装では URL クエリに含まれる）
        body = email_backend.sent[0]["body"]
        # token=... の部分を抽出
        import re
        token_match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
        token = token_match.group(1)

        await provider.confirm_password_reset(token, "NewPass456")
        # 新パスワードでログインできる
        pair = await provider.authenticate("a@b.com", "NewPass456", ip="1.1.1.1")
        assert pair.access_token
        # 旧パスワードは不可
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "OldPass123", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_confirm_token_only_once(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "OldPass123")
        await provider.request_password_reset("a@b.com")
        import re
        token = re.search(r"token=([A-Za-z0-9_\-]+)", email_backend.sent[0]["body"]).group(1)
        await provider.confirm_password_reset(token, "NewPass456")
        # 同じトークンは 2 回目失敗
        with pytest.raises(InvalidToken):
            await provider.confirm_password_reset(token, "OtherPass789")
```

- [ ] **Step 3: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_local_provider.py -v
```

- [ ] **Step 4: 設定（先に最低限）**

`api/lib/config.py` に追加（既存に上書きしない、新規追加のみ）:

```python
# 認証プロバイダ
auth_provider: str = "supabase"
jwt_secret: Optional[str] = None
jwt_audience: str = "authenticated"
jwt_issuer: str = "geo-base"
access_token_ttl_seconds: int = 900

# メール
email_backend: str = "console"
smtp_host: Optional[str] = None
smtp_port: int = 587
smtp_user: Optional[str] = None
smtp_password: Optional[str] = None
smtp_from: Optional[str] = None
smtp_use_tls: bool = True

# 招待
invitation_base_url: str = "http://localhost:3000"

# Cookie
cookie_samesite: str = "lax"
cookie_secure: bool = False
cookie_domain: Optional[str] = None

# CORS（既存 cors_origins と統合）
# API キーログサンプリング
api_key_log_sample_rate: float = 1.0
```

`Settings` クラスに `effective_jwt_secret` プロパティを追加:

```python
@property
def effective_jwt_secret(self) -> Optional[str]:
    """JWT_SECRET 優先、SUPABASE_JWT_SECRET にフォールバック"""
    return self.jwt_secret or self.supabase_jwt_secret
```

- [ ] **Step 5: 実装**

`api/lib/_auth_pkg/providers/local.py`:

```python
"""LocalAuthProvider - geo-base が users テーブルを所有し JWT を発行する実装。"""
import asyncio
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from lib.config import get_settings
from lib.database import get_connection_context  # 既存ヘルパー想定。なければ get_connection を使う

from ..errors import (
    AuthError, InvalidCredentials, RateLimited, UserAlreadyExists,
    UserNotFound, InvalidToken, WeakPassword,
)
from ..models import User, AuthResult, TokenPair
from ..provider import AuthProvider
from ..jwt_utils import issue_access_token, decode_access_token, claims_to_user
from ..password import hash_password, verify_password, check_password_policy
from ..tokens import (
    issue_refresh_token, verify_and_rotate_refresh_token,
    revoke_refresh_token, revoke_all_user_tokens,
)
from ..rate_limit import check_login_rate_limit, record_login_attempt
from ..email_backends import get_email_backend
from ..email_backends.templates import render_password_reset_email


logger = logging.getLogger(__name__)


# タイミング攻撃対策用のダミーハッシュ（モジュール load 時に 1 回だけ計算）
_DUMMY_HASH = hash_password("__dummy_for_timing_attack_mitigation__")

PASSWORD_RESET_TTL_HOURS = 1


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_db_connection():
    """既存の database モジュールから接続を取得"""
    from lib.database import get_connection
    # get_connection は context manager を返す想定
    return get_connection()


class LocalAuthProvider(AuthProvider):
    """素の PostgreSQL 上で動く認証プロバイダ。"""

    def __init__(self):
        self._settings = get_settings()

    # ============ Token verification ============

    async def verify_access_token(self, token: str) -> AuthResult:
        try:
            secret = self._settings.effective_jwt_secret
            claims = await asyncio.to_thread(
                decode_access_token,
                token,
                secret=secret,
                audience=self._settings.jwt_audience,
            )
            user = claims_to_user(claims)
            return AuthResult(is_authenticated=True, user=user)
        except InvalidToken as e:
            return AuthResult(is_authenticated=False, error=str(e))
        except Exception as e:
            logger.error("Unexpected error verifying token", exc_info=e)
            return AuthResult(is_authenticated=False, error="Token verification failed")

    # ============ User lookup ============

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        return await asyncio.to_thread(self._get_user_by_id_sync, user_id)

    def _get_user_by_id_sync(self, user_id: str) -> Optional[User]:
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at, is_active
                       FROM users WHERE id = %s""",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row[0]), email=row[1], name=row[2], role=row[3],
                    app_metadata=row[4] or {}, user_metadata=row[5] or {},
                    email_verified=row[6] is not None,
                )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await asyncio.to_thread(self._get_user_by_email_sync, email)

    def _get_user_by_email_sync(self, email: str) -> Optional[User]:
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at
                       FROM users WHERE email = %s AND is_active = TRUE""",
                    (email.lower(),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row[0]), email=row[1], name=row[2], role=row[3],
                    app_metadata=row[4] or {}, user_metadata=row[5] or {},
                    email_verified=row[6] is not None,
                )

    # ============ Authentication ============

    async def authenticate(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        return await asyncio.to_thread(
            self._authenticate_sync, email, password, ip, user_agent
        )

    def _authenticate_sync(self, email, password, ip, user_agent) -> TokenPair:
        with _get_db_connection() as conn:
            check_login_rate_limit(conn, email=email, ip=ip)

            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, password_hash, name, role, app_metadata, user_metadata, email, email_verified_at
                       FROM users WHERE email = %s AND is_active = TRUE""",
                    (email.lower(),),
                )
                row = cur.fetchone()

            if row is None:
                # タイミング攻撃対策: ユーザー不存在でも bcrypt 検証
                verify_password(password, _DUMMY_HASH)
                record_login_attempt(conn, email=email, success=False, ip=ip, user_agent=user_agent)
                raise InvalidCredentials("Invalid email or password")

            user_id, password_hash, name, role, app_meta, user_meta, db_email, email_verified_at = row

            if not verify_password(password, password_hash):
                record_login_attempt(conn, email=email, success=False, ip=ip, user_agent=user_agent)
                raise InvalidCredentials("Invalid email or password")

            record_login_attempt(conn, email=email, success=True, ip=ip, user_agent=user_agent)

            # last_login_at 更新
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user_id,))

            user = User(
                id=str(user_id), email=db_email, name=name, role=role,
                app_metadata=app_meta or {}, user_metadata=user_meta or {},
                email_verified=email_verified_at is not None,
            )

            access_token = issue_access_token(
                user,
                secret=self._settings.effective_jwt_secret,
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                ttl_seconds=self._settings.access_token_ttl_seconds,
            )
            refresh_token = issue_refresh_token(
                conn, str(user_id), ip=ip, user_agent=user_agent
            )

            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self._settings.access_token_ttl_seconds,
            )

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        return await asyncio.to_thread(
            self._refresh_tokens_sync, refresh_token, ip, user_agent
        )

    def _refresh_tokens_sync(self, refresh_token, ip, user_agent) -> TokenPair:
        with _get_db_connection() as conn:
            user_id, new_refresh = verify_and_rotate_refresh_token(
                conn, refresh_token, ip=ip, user_agent=user_agent
            )
            user = self._get_user_by_id_sync(user_id)
            if user is None:
                raise InvalidToken("User not found")

            access_token = issue_access_token(
                user,
                secret=self._settings.effective_jwt_secret,
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                ttl_seconds=self._settings.access_token_ttl_seconds,
            )
            return TokenPair(
                access_token=access_token,
                refresh_token=new_refresh,
                expires_in=self._settings.access_token_ttl_seconds,
            )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        await asyncio.to_thread(self._revoke_refresh_sync, refresh_token)

    def _revoke_refresh_sync(self, refresh_token: str) -> None:
        with _get_db_connection() as conn:
            revoke_refresh_token(conn, refresh_token, reason="logout")

    # ============ User CRUD ============

    async def create_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
        email_verified: bool = False,
        app_metadata: Optional[dict] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        check_password_policy(password)
        return await asyncio.to_thread(
            self._create_user_sync, email, password, name,
            email_verified, app_metadata, user_metadata,
        )

    def _create_user_sync(self, email, password, name, email_verified, app_meta, user_meta) -> User:
        import json
        password_hash_str = hash_password(password)
        email_lower = email.lower()

        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE email = %s", (email_lower,))
                if cur.fetchone():
                    raise UserAlreadyExists(f"User with email {email_lower} already exists")

                cur.execute(
                    """INSERT INTO users 
                          (email, password_hash, name, email_verified_at, app_metadata, user_metadata)
                       VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                       RETURNING id, email, name, role, app_metadata, user_metadata, email_verified_at""",
                    (
                        email_lower, password_hash_str, name,
                        datetime.now(timezone.utc) if email_verified else None,
                        json.dumps(app_meta or {}),
                        json.dumps(user_meta or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        return User(
            id=str(row[0]), email=row[1], name=row[2], role=row[3],
            app_metadata=row[4] or {}, user_metadata=row[5] or {},
            email_verified=row[6] is not None,
        )

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        return await asyncio.to_thread(
            self._update_user_sync, user_id, name, email, user_metadata
        )

    def _update_user_sync(self, user_id, name, email, user_metadata) -> User:
        import json
        updates = []
        params = []
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if email is not None:
            updates.append("email = %s")
            params.append(email.lower())
        if user_metadata is not None:
            updates.append("user_metadata = %s::jsonb")
            params.append(json.dumps(user_metadata))

        if not updates:
            user = self._get_user_by_id_sync(user_id)
            if not user:
                raise UserNotFound(user_id)
            return user

        params.append(user_id)
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"""UPDATE users SET {', '.join(updates)}, updated_at = NOW()
                            WHERE id = %s
                            RETURNING id, email, name, role, app_metadata, user_metadata, email_verified_at""",
                        tuple(params),
                    )
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                        raise UserAlreadyExists(f"Email already in use")
                    raise
                row = cur.fetchone()
                if not row:
                    raise UserNotFound(user_id)
            conn.commit()

        return User(
            id=str(row[0]), email=row[1], name=row[2], role=row[3],
            app_metadata=row[4] or {}, user_metadata=row[5] or {},
            email_verified=row[6] is not None,
        )

    async def update_password(self, user_id: str, new_password: str) -> None:
        check_password_policy(new_password)
        await asyncio.to_thread(self._update_password_sync, user_id, new_password)

    def _update_password_sync(self, user_id, new_password):
        password_hash_str = hash_password(new_password)
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (password_hash_str, user_id),
                )
                if cur.rowcount == 0:
                    raise UserNotFound(user_id)
            conn.commit()

    # ============ Password reset ============

    async def request_password_reset(self, email: str, ip: Optional[str] = None) -> None:
        await asyncio.to_thread(self._request_reset_sync, email, ip)

    def _request_reset_sync(self, email, ip):
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name FROM users WHERE email = %s AND is_active = TRUE",
                    (email.lower(),),
                )
                row = cur.fetchone()

            if row is None:
                logger.info("Password reset requested for nonexistent email", extra={"email": email})
                return  # 情報漏洩防止: 何もしないが正常終了

            user_id, user_name = row

            token = secrets.token_urlsafe(48)
            token_hash = _hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TTL_HOURS)

            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, ip_address)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, token_hash, expires_at, ip),
                )
            conn.commit()

        # メール送信（非同期だが asyncio.to_thread の同期コンテキストで呼ぶため、
        # email_backend.send は coroutine なので別スレッドの新しい event loop で実行）
        reset_url = f"{self._settings.invitation_base_url}/password-reset/confirm?token={token}"
        subject, body = render_password_reset_email(
            user_name=user_name, reset_url=reset_url, expires_at=expires_at,
        )
        backend = get_email_backend()
        # asyncio.to_thread から呼ばれているのでイベントループはない
        # → 専用ループで実行
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(backend.send(email, subject, body))
        finally:
            loop.close()

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        check_password_policy(new_password)
        return await asyncio.to_thread(self._confirm_reset_sync, token, new_password)

    def _confirm_reset_sync(self, token, new_password) -> User:
        token_hash = _hash_token(token)
        password_hash_str = hash_password(new_password)

        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, user_id, used_at, expires_at
                       FROM password_reset_tokens WHERE token_hash = %s
                       FOR UPDATE""",
                    (token_hash,),
                )
                row = cur.fetchone()

                if not row:
                    raise InvalidToken("Reset token not found")

                token_id, user_id, used_at, expires_at = row

                if used_at is not None:
                    raise InvalidToken("Reset token already used")

                if expires_at < datetime.now(timezone.utc):
                    raise InvalidToken("Reset token expired")

                cur.execute(
                    "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (password_hash_str, user_id),
                )
                cur.execute(
                    "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
                    (token_id,),
                )
                # 全 refresh token 失効
                cur.execute(
                    """UPDATE refresh_tokens SET revoked_at = NOW(), revoked_reason = 'password_reset'
                       WHERE user_id = %s AND revoked_at IS NULL""",
                    (user_id,),
                )

                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at
                       FROM users WHERE id = %s""",
                    (user_id,),
                )
                user_row = cur.fetchone()
            conn.commit()

        return User(
            id=str(user_row[0]), email=user_row[1], name=user_row[2], role=user_row[3],
            app_metadata=user_row[4] or {}, user_metadata=user_row[5] or {},
            email_verified=user_row[6] is not None,
        )
```

注: 上記コードは `lib.database.get_connection()` がコンテキストマネージャを返すことを前提としています。既存の database モジュールがそうなっていない場合、このタスク内で適切なヘルパー（`get_connection_context()`）を `lib/database.py` に追加してください。

- [ ] **Step 6: database.py の context manager 確認・追加**

```bash
cd api && grep -n "@contextmanager\|def get_connection" lib/database.py | head -10
```

既存に `@contextmanager` 付きの `get_connection_context` があるか、`get_connection` 自体が context manager を返すか確認。

なければ `lib/database.py` に追加:

```python
from contextlib import contextmanager

@contextmanager
def get_connection_context():
    """同期 with 文向けの connection context manager."""
    conn = get_connection()
    try:
        yield conn
    finally:
        if hasattr(conn, "close"):
            conn.close()
```

そして `local.py` の `_get_db_connection` を `get_connection_context()` を返すよう修正。

- [ ] **Step 7: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_local_provider.py -v
```

期待: 全テスト PASS（DB 関連でエラーが出る場合、`lib/database.py` の調整が必要）

- [ ] **Step 8: コミット**

```bash
git add api/lib/_auth_pkg/providers/ api/lib/config.py api/lib/database.py api/tests/test_auth/test_local_provider.py
git commit -m "feat(auth): add LocalAuthProvider with full auth flow"
```

### Task 2.3: `SupabaseAuthProvider`

**Files:**
- Create: `api/lib/_auth_pkg/providers/supabase.py`
- Create: `api/tests/test_auth/test_supabase_provider.py`

- [ ] **Step 1: テスト作成（respx で HTTP モック）**

`api/tests/test_auth/test_supabase_provider.py`:

```python
"""Tests for SupabaseAuthProvider (HTTP mocked)."""
import pytest
import respx
from httpx import Response

from lib._auth_pkg.providers.supabase import SupabaseAuthProvider
from lib._auth_pkg.errors import (
    InvalidCredentials, UserAlreadyExists, InvalidToken, ProviderError,
)


SUPABASE_URL = "https://test.supabase.co"


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-" + "x" * 50)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    from lib.config import get_settings
    get_settings.cache_clear()
    return SupabaseAuthProvider()


class TestAuthenticate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(200, json={
                "access_token": "fake.jwt.token",
                "refresh_token": "fake-refresh",
                "expires_in": 3600,
                "user": {"id": "user-123", "email": "a@b.com", "role": "authenticated"},
            })
        )
        pair = await provider.authenticate("a@b.com", "MyPass123")
        assert pair.access_token == "fake.jwt.token"
        assert pair.refresh_token == "fake-refresh"

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_credentials(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(400, json={
                "error": "invalid_grant",
                "error_description": "Invalid login credentials",
            })
        )
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "wrong")

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_raises_provider_error(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(500)
        )
        with pytest.raises(ProviderError):
            await provider.authenticate("a@b.com", "MyPass123")


class TestCreateUser:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={
                "id": "user-456", "email": "new@example.com",
                "user_metadata": {"name": "Bob"}, "email_confirmed_at": "2026-05-08T00:00:00Z",
            })
        )
        u = await provider.create_user("new@example.com", "ValidPass123", name="Bob")
        assert u.id == "user-456"
        assert u.email == "new@example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_duplicate(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(422, json={"error": "user_already_exists"})
        )
        with pytest.raises(UserAlreadyExists):
            await provider.create_user("dupe@example.com", "ValidPass123")


class TestVerifyAccessToken:
    @pytest.mark.asyncio
    async def test_uses_local_jwt_verification(self, provider):
        # Supabase mode でも JWT 検証はローカルで行われる
        from lib._auth_pkg.jwt_utils import issue_access_token
        from lib._auth_pkg.models import User
        u = User(id="abc", email="a@b.com", role="authenticated")
        token = issue_access_token(
            u, secret="test-jwt-secret-" + "x" * 50,
            audience="authenticated",
        )
        result = await provider.verify_access_token(token)
        assert result.is_authenticated
        assert result.user.id == "abc"


class TestGetUserByEmail:
    @pytest.mark.asyncio
    @respx.mock
    async def test_found(self, provider):
        respx.get(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={
                "users": [{"id": "u1", "email": "a@b.com"}]
            })
        )
        u = await provider.get_user_by_email("a@b.com")
        assert u.id == "u1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found(self, provider):
        respx.get(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={"users": []})
        )
        u = await provider.get_user_by_email("nobody@example.com")
        assert u is None
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_supabase_provider.py -v
```

- [ ] **Step 3: 実装**

`api/lib/_auth_pkg/providers/supabase.py`:

```python
"""SupabaseAuthProvider - Supabase Auth REST API のラッパー。"""
import logging
from typing import Optional

import httpx

from lib.config import get_settings

from ..errors import (
    AuthError, InvalidCredentials, InvalidToken,
    UserAlreadyExists, UserNotFound, ProviderError, WeakPassword,
)
from ..models import User, AuthResult, TokenPair
from ..provider import AuthProvider
from ..jwt_utils import decode_access_token, claims_to_user


logger = logging.getLogger(__name__)


class SupabaseAuthProvider(AuthProvider):
    """Supabase Auth REST API へ委譲する実装。"""

    def __init__(self):
        self._settings = get_settings()
        self._base = self._settings.supabase_url
        self._service_key = self._settings.supabase_service_role_key
        self._timeout = httpx.Timeout(30.0)

    def _admin_headers(self) -> dict:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Content-Type": "application/json",
        }

    def _public_headers(self) -> dict:
        return {
            "apikey": self._service_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, headers: dict, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                return await client.request(method, f"{self._base}{path}", headers=headers, **kwargs)
            except httpx.HTTPError as e:
                raise ProviderError(f"Supabase request failed: {e}")

    def _user_from_supabase(self, data: dict) -> User:
        return User(
            id=data["id"],
            email=data.get("email"),
            role=data.get("role", "authenticated"),
            name=(data.get("user_metadata") or {}).get("name"),
            app_metadata=data.get("app_metadata"),
            user_metadata=data.get("user_metadata"),
            email_verified=data.get("email_confirmed_at") is not None,
        )

    async def verify_access_token(self, token: str) -> AuthResult:
        try:
            claims = decode_access_token(
                token,
                secret=self._settings.effective_jwt_secret,
                audience=self._settings.jwt_audience,
            )
            return AuthResult(is_authenticated=True, user=claims_to_user(claims))
        except InvalidToken as e:
            return AuthResult(is_authenticated=False, error=str(e))

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        res = await self._request("GET", f"/auth/v1/admin/users/{user_id}", self._admin_headers())
        if res.status_code == 404:
            return None
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            return None
        return self._user_from_supabase(res.json())

    async def get_user_by_email(self, email: str) -> Optional[User]:
        res = await self._request(
            "GET", "/auth/v1/admin/users",
            self._admin_headers(),
            params={"filter": f"email=eq.{email.lower()}"},
        )
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        users = res.json().get("users", [])
        if not users:
            return None
        return self._user_from_supabase(users[0])

    async def authenticate(self, email, password, ip=None, user_agent=None) -> TokenPair:
        res = await self._request(
            "POST", "/auth/v1/token",
            self._public_headers(),
            params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        if res.status_code == 400:
            raise InvalidCredentials("Invalid email or password")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            raise InvalidCredentials("Authentication failed")

        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def refresh_tokens(self, refresh_token, ip=None, user_agent=None) -> TokenPair:
        res = await self._request(
            "POST", "/auth/v1/token",
            self._public_headers(),
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
        )
        if res.status_code == 400:
            raise InvalidToken("Invalid refresh token")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")

        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        # Supabase の logout は access_token 必要だが、refresh だけで動く auth/v1/logout は API 仕様による
        # Phase 3 では best-effort で送る
        await self._request(
            "POST", "/auth/v1/logout",
            {**self._public_headers(), "Authorization": f"Bearer {refresh_token}"},
        )

    async def create_user(
        self, email, password, name=None, email_verified=False,
        app_metadata=None, user_metadata=None,
    ) -> User:
        body = {
            "email": email.lower(),
            "password": password,
            "email_confirm": email_verified,
        }
        if name is not None:
            body["user_metadata"] = {"name": name, **(user_metadata or {})}
        elif user_metadata is not None:
            body["user_metadata"] = user_metadata
        if app_metadata is not None:
            body["app_metadata"] = app_metadata

        res = await self._request("POST", "/auth/v1/admin/users", self._admin_headers(), json=body)
        if res.status_code in (422, 409):
            raise UserAlreadyExists("Email already registered")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code not in (200, 201):
            raise ProviderError(f"User creation failed: {res.status_code}")

        return self._user_from_supabase(res.json())

    async def update_user(self, user_id, name=None, email=None, user_metadata=None) -> User:
        body = {}
        if email is not None:
            body["email"] = email.lower()
        if name is not None or user_metadata is not None:
            meta = user_metadata or {}
            if name is not None:
                meta["name"] = name
            body["user_metadata"] = meta

        if not body:
            user = await self.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound(user_id)
            return user

        res = await self._request("PUT", f"/auth/v1/admin/users/{user_id}", self._admin_headers(), json=body)
        if res.status_code == 404:
            raise UserNotFound(user_id)
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            raise ProviderError(f"User update failed: {res.status_code}")
        return self._user_from_supabase(res.json())

    async def update_password(self, user_id: str, new_password: str) -> None:
        res = await self._request(
            "PUT", f"/auth/v1/admin/users/{user_id}",
            self._admin_headers(),
            json={"password": new_password},
        )
        if res.status_code == 404:
            raise UserNotFound(user_id)
        if res.status_code != 200:
            raise ProviderError(f"Password update failed: {res.status_code}")

    async def request_password_reset(self, email: str, ip=None) -> None:
        # Supabase が自動でメール送信する
        await self._request(
            "POST", "/auth/v1/recover",
            self._public_headers(),
            json={"email": email.lower()},
        )
        # エラーは無視（情報漏洩防止）

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        # Supabase の recovery token は OTP として verify する
        res = await self._request(
            "POST", "/auth/v1/verify",
            self._public_headers(),
            json={"type": "recovery", "token": token},
        )
        if res.status_code >= 400:
            raise InvalidToken("Invalid recovery token")

        data = res.json()
        access_token = data.get("access_token")
        user_id = data.get("user", {}).get("id")
        if not access_token or not user_id:
            raise InvalidToken("Recovery token did not return user")

        # 認証状態でパスワード更新
        res2 = await self._request(
            "PUT", "/auth/v1/user",
            {**self._public_headers(), "Authorization": f"Bearer {access_token}"},
            json={"password": new_password},
        )
        if res2.status_code != 200:
            raise ProviderError(f"Password update failed: {res2.status_code}")
        return self._user_from_supabase(res2.json())
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_supabase_provider.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/_auth_pkg/providers/supabase.py api/tests/test_auth/test_supabase_provider.py
git commit -m "feat(auth): add SupabaseAuthProvider via REST API"
```

### Task 2.4: ファクトリと `__init__.py`

**Files:**
- Modify: `api/lib/_auth_pkg/__init__.py`
- Modify: `api/tests/test_auth/test_factory.py`（factory テスト追加）

- [ ] **Step 1: テスト追加**

`api/tests/test_auth/test_factory.py` に以下を追加:

```python
class TestFactory:
    def test_local_provider_selected(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        from lib.config import get_settings
        from lib._auth_pkg import get_auth_provider
        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        from lib._auth_pkg.providers.local import LocalAuthProvider
        assert isinstance(get_auth_provider(), LocalAuthProvider)

    def test_supabase_provider_selected(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "x" * 64)
        from lib.config import get_settings
        from lib._auth_pkg import get_auth_provider
        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        from lib._auth_pkg.providers.supabase import SupabaseAuthProvider
        assert isinstance(get_auth_provider(), SupabaseAuthProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "unknown")
        from lib.config import get_settings
        from lib._auth_pkg import get_auth_provider
        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        import pytest
        with pytest.raises(ValueError):
            get_auth_provider()
```

- [ ] **Step 2: `__init__.py` 実装（factory + 互換 re-export）**

`api/lib/_auth_pkg/__init__.py`:

```python
"""auth パッケージ。

公開シンボル:
- User, AuthResult, TokenPair: モデル
- AuthError 系: エラー階層
- AuthProvider: 抽象インタフェース
- get_auth_provider(): factory
- require_auth, get_current_user: FastAPI dependencies (既存互換)
- verify_jwt_token: 後方互換用エイリアス
- extract_token_from_header: 既存ヘルパ
- check_tileset_access, get_tileset_with_access_check, is_auth_configured: 既存タイル系認可
"""
from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header, status

from .errors import (
    AuthError, InvalidCredentials, RateLimited, UserNotFound,
    UserAlreadyExists, InvalidToken, WeakPassword, ProviderError,
)
from .models import User, AuthResult, TokenPair
from .provider import AuthProvider


@lru_cache(maxsize=1)
def get_auth_provider() -> AuthProvider:
    """環境変数 AUTH_PROVIDER からプロバイダを選択。"""
    from lib.config import get_settings
    settings = get_settings()

    if settings.auth_provider == "local":
        from .providers.local import LocalAuthProvider
        return LocalAuthProvider()
    elif settings.auth_provider == "supabase":
        from .providers.supabase import SupabaseAuthProvider
        return SupabaseAuthProvider()

    raise ValueError(f"Unknown AUTH_PROVIDER: {settings.auth_provider}")


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """Authorization ヘッダから 'Bearer xxx' の xxx を取り出す。"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1]


# === 後方互換エイリアス ===
def verify_jwt_token(token: str) -> AuthResult:
    """既存コード互換。新規コードは get_auth_provider().verify_access_token() を使うこと。"""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        get_auth_provider().verify_access_token(token)
    )


# === FastAPI Dependencies ===

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[User]:
    """認証済みユーザーを返す。未認証なら None（例外なし）。"""
    if not authorization:
        return None
    token = extract_token_from_header(authorization)
    if not token:
        return None

    result = await get_auth_provider().verify_access_token(token)
    if result.is_authenticated and result.user:
        return result.user
    return None


async def require_auth(
    authorization: Annotated[Optional[str], Header()] = None,
) -> User:
    """認証必須。失敗時 401。"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await get_auth_provider().verify_access_token(token)
    if not result.is_authenticated or not result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result.user


# === 既存タイル認可関数（既存 auth.py から移設） ===

def check_tileset_access(
    tileset_id: str,
    is_public: bool,
    owner_user_id: Optional[str],
    current_user: Optional[User],
) -> bool:
    """旧来のタイルセットアクセスチェック（後方互換）。

    新規コードは AuthContext + check_tileset_access_v2 を使うこと。
    """
    if is_public:
        return True
    if not current_user:
        return False
    if owner_user_id and current_user.id == owner_user_id:
        return True
    return False


async def get_tileset_with_access_check(
    tileset_id: str,
    conn,
    current_user: Optional[User],
) -> dict:
    """既存 auth.py から移設。新規コードは AuthContext 版を使うこと。"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, description, type, format, min_zoom, max_zoom,
                      is_public, user_id, metadata, created_at, updated_at
               FROM tilesets WHERE id = %s""",
            (tileset_id,),
        )
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, f"Tileset not found: {tileset_id}")

    tileset = dict(zip(columns, row))
    is_public = tileset.get("is_public", True)
    owner_user_id = str(tileset.get("user_id")) if tileset.get("user_id") else None

    if not is_public and not current_user:
        raise HTTPException(401, "Authentication required to access this tileset",
                            headers={"WWW-Authenticate": "Bearer"})

    if not check_tileset_access(tileset_id, is_public, owner_user_id, current_user):
        raise HTTPException(403, "You do not have permission to access this tileset")

    return tileset


def is_auth_configured() -> bool:
    """認証が正しく設定されているかチェック（後方互換）。"""
    from lib.config import get_settings
    return bool(get_settings().effective_jwt_secret)


__all__ = [
    # Models
    "User", "AuthResult", "TokenPair",
    # Errors
    "AuthError", "InvalidCredentials", "RateLimited", "UserNotFound",
    "UserAlreadyExists", "InvalidToken", "WeakPassword", "ProviderError",
    # Provider
    "AuthProvider", "get_auth_provider",
    # Dependencies
    "get_current_user", "require_auth",
    # Helpers
    "extract_token_from_header", "verify_jwt_token",
    # Tile access (legacy)
    "check_tileset_access", "get_tileset_with_access_check", "is_auth_configured",
]
```

- [ ] **Step 3: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_factory.py -v
```

- [ ] **Step 4: コミット**

```bash
git add api/lib/_auth_pkg/__init__.py api/tests/test_auth/test_factory.py
git commit -m "feat(auth): add AuthProvider factory and __init__ with backward-compat exports"
```

### Task 2.5: 既存 `auth.py` を `auth/` パッケージに置き換え

**Files:**
- Rename: `api/lib/_auth_pkg/` → `api/lib/auth/`
- Delete: `api/lib/auth.py`

- [ ] **Step 1: 既存 import の利用箇所確認**

```bash
cd api && grep -rn "from lib.auth import\|import lib.auth" lib/ tests/ | grep -v "_auth_pkg" | head -30
```

期待: `from lib.auth import User, require_auth, ...` 等の既存利用箇所一覧。

- [ ] **Step 2: パッケージリネーム**

```bash
cd api/lib
git mv _auth_pkg auth_new
# 元の auth.py を保存（バックアップ）
git mv auth.py auth_old.py
# 新パッケージを auth に
git mv auth_new auth
# 古い auth.py を削除
git rm auth_old.py
```

- [ ] **Step 3: テスト内 import パス更新**

```bash
cd api
# テストファイルで lib._auth_pkg → lib.auth に置換
find tests -name "*.py" -exec sed -i.bak 's/lib\._auth_pkg/lib.auth/g' {} \;
find tests -name "*.bak" -delete
```

- [ ] **Step 4: ソース内 import パス更新**

```bash
# 万が一 lib._auth_pkg を参照しているソースも更新
find lib -name "*.py" -exec sed -i.bak 's/lib\._auth_pkg/lib.auth/g' {} \;
find lib -name "*.bak" -delete
```

- [ ] **Step 5: 全テスト実行**

```bash
cd api && uv run pytest tests/ -v 2>&1 | tail -30
```

期待: 既存テストも新規 auth テストも全て PASS。

- [ ] **Step 6: 既存ルーター動作確認（実際にサーバー起動）**

```bash
cd api && uv run uvicorn lib.main:app --port 8000 &
sleep 3
curl http://localhost:8000/api/health
kill %1
```

期待: 起動成功、/api/health が 200 を返す。

- [ ] **Step 7: コミット**

```bash
git add -A
git commit -m "refactor(auth): replace auth.py with auth/ package, all imports backward compatible"
```

---


## Phase 3: AuthContext と API キー認証

### Task 3.1: `context.py` (AuthContext)

**Files:**
- Create: `api/lib/auth/context.py`
- Create: `api/tests/test_auth/test_context.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_context.py`:

```python
"""Tests for AuthContext."""
import pytest
from lib.auth.context import AuthContext
from lib.auth.models import User


class TestFromJwtUser:
    def test_basic(self):
        u = User(id="abc", email="a@b.com", role="authenticated")
        ctx = AuthContext.from_jwt_user(u)
        assert ctx.user_id == "abc"
        assert ctx.email == "a@b.com"
        assert ctx.is_api_key is False
        assert ctx.team_id is None
        assert "read" in ctx.scopes
        assert "write" in ctx.scopes


class TestFromApiKey:
    def test_basic(self):
        key_data = {
            "id": "key-1", "user_id": "user-1", "team_id": "team-1",
            "scopes": ["read"],
        }
        ctx = AuthContext.from_api_key(key_data)
        assert ctx.is_api_key is True
        assert ctx.user_id == "user-1"
        assert ctx.team_id == "team-1"
        assert ctx.scopes == ["read"]
        assert ctx.api_key_id == "key-1"

    def test_no_team(self):
        key_data = {"id": "k", "user_id": "u", "team_id": None, "scopes": ["read"]}
        ctx = AuthContext.from_api_key(key_data)
        assert ctx.team_id is None


class TestHasScope:
    @pytest.mark.parametrize("scopes,required,expected", [
        (["read"], "read", True),
        (["read"], "write", False),
        (["write"], "read", True),  # write 含意 read
        (["delete"], "write", True),
        (["delete"], "read", True),
        (["admin"], "delete", True),
        (["admin"], "read", True),
        (["admin"], "admin", True),
        ([], "read", False),
    ])
    def test_scope_hierarchy(self, scopes, required, expected):
        ctx = AuthContext(user_id="u", scopes=scopes)
        assert ctx.has_scope(required) is expected
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_context.py -v
```

- [ ] **Step 3: 実装**

`api/lib/auth/context.py`:

```python
"""AuthContext - JWT ユーザーと API キーを統一的に扱うコンテキスト。"""
from typing import Optional
from pydantic import BaseModel

from .models import User


# スコープ階層（数値が大きいほど強い権限）
_SCOPE_HIERARCHY = {"read": 1, "write": 2, "delete": 3, "admin": 4}


class AuthContext(BaseModel):
    """JWT ユーザーと API キーの統一コンテキスト。"""

    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[str] = None  # API キー時のみ
    scopes: list[str] = []
    is_api_key: bool = False
    api_key_id: Optional[str] = None

    @classmethod
    def from_jwt_user(cls, user: User) -> "AuthContext":
        """JWT 認証結果から作成。フルスコープを付与。"""
        return cls(
            user_id=user.id,
            email=user.email,
            role=user.role,
            scopes=["read", "write", "delete", "admin"],
            is_api_key=False,
        )

    @classmethod
    def from_api_key(cls, key_data: dict) -> "AuthContext":
        """API キー DB レコードから作成。"""
        return cls(
            user_id=str(key_data["user_id"]),
            team_id=str(key_data["team_id"]) if key_data.get("team_id") else None,
            scopes=list(key_data.get("scopes") or []),
            is_api_key=True,
            api_key_id=str(key_data["id"]),
        )

    def has_scope(self, required: str) -> bool:
        """admin > delete > write > read の階層で判定。"""
        if not self.scopes:
            return False
        required_level = _SCOPE_HIERARCHY.get(required, 0)
        max_level = max(_SCOPE_HIERARCHY.get(s, 0) for s in self.scopes)
        return max_level >= required_level
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_context.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/auth/context.py api/tests/test_auth/test_context.py
git commit -m "feat(auth): add AuthContext for unified JWT/API key handling"
```

### Task 3.2: `api_key_auth.py` (API キー検証)

**Files:**
- Create: `api/lib/auth/api_key_auth.py`
- Create: `api/tests/test_auth/test_api_key_auth.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_api_key_auth.py`:

```python
"""Tests for api_key_auth module."""
import pytest
import hashlib
from datetime import datetime, timedelta, timezone

from lib.auth.api_key_auth import validate_api_key
from lib.auth.errors import InvalidToken, RateLimited
from lib.auth.context import AuthContext


@pytest.fixture
def make_api_key(db_conn, clean_auth_tables):
    """API キーを発行するファクトリ"""
    import secrets, json
    created_keys = []

    def _make(scopes=None, team_id=None, rate_limit_per_minute=60, rate_limit_per_day=10000,
              is_active=True, expires_at=None, revoked_at=None):
        scopes = scopes or ["read"]
        random_part = secrets.token_urlsafe(32)
        full_key = f"gb_test_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        prefix = full_key[:12]
        user_id = "00000000-0000-0000-0000-000000000001"

        # ダミーユーザーがいなくても api_keys は user_id FK なしなので OK
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_keys 
                      (name, prefix, key_hash, user_id, team_id, scopes,
                       rate_limit_per_minute, rate_limit_per_day, is_active, expires_at, revoked_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                ("test", prefix, key_hash, user_id, team_id, scopes,
                 rate_limit_per_minute, rate_limit_per_day, is_active, expires_at, revoked_at),
            )
            key_id = cur.fetchone()[0]
        db_conn.commit()
        created_keys.append((full_key, key_id))
        return full_key, key_id

    return _make


class TestValidateApiKey:
    @pytest.mark.asyncio
    async def test_valid_key(self, make_api_key, db_conn):
        full_key, key_id = make_api_key(scopes=["read", "write"])
        ctx = await validate_api_key(full_key)
        assert ctx is not None
        assert ctx.is_api_key
        assert "read" in ctx.scopes
        assert ctx.api_key_id == str(key_id)

    @pytest.mark.asyncio
    async def test_revoked_key(self, make_api_key, db_conn):
        full_key, _ = make_api_key(revoked_at=datetime.now(timezone.utc))
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_inactive_key(self, make_api_key, db_conn):
        full_key, _ = make_api_key(is_active=False)
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_expired_key(self, make_api_key, db_conn):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        full_key, _ = make_api_key(expires_at=past)
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_unknown_key(self):
        ctx = await validate_api_key("gb_live_unknown")
        assert ctx is None

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, make_api_key, db_conn):
        full_key, key_id = make_api_key(rate_limit_per_minute=2)
        # 2 回までは OK
        await validate_api_key(full_key)
        await validate_api_key(full_key)
        # 3 回目で RateLimited
        with pytest.raises(RateLimited):
            await validate_api_key(full_key)

    @pytest.mark.asyncio
    async def test_team_id_in_context(self, make_api_key, db_conn):
        team_id = "11111111-1111-1111-1111-111111111111"
        # team_id を有効にするには teams テーブルにレコードが必要
        # 簡略化のため team_id NULL のテストで十分
        full_key, _ = make_api_key(team_id=None)
        ctx = await validate_api_key(full_key)
        assert ctx.team_id is None
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_api_key_auth.py -v
```

- [ ] **Step 3: 実装**

`api/lib/auth/api_key_auth.py`:

```python
"""API キー検証 + AuthContext 化 + レート制限統合。"""
import asyncio
import hashlib
import logging
from typing import Optional

from .context import AuthContext
from .errors import RateLimited


logger = logging.getLogger(__name__)


API_KEY_PREFIX = "gb_"  # gb_live_xxx or gb_test_xxx


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


async def validate_api_key(
    key: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[AuthContext]:
    """API キーを検証して AuthContext を返す。

    Returns:
        AuthContext: 有効なキーの場合
        None: キーが見つからない / 無効 / revoked / 期限切れ

    Raises:
        RateLimited: レート制限超過
    """
    return await asyncio.to_thread(_validate_sync, key, ip, user_agent)


def _validate_sync(key: str, ip: Optional[str], user_agent: Optional[str]) -> Optional[AuthContext]:
    from lib.database import get_connection_context

    key_hash = _hash_key(key)

    with get_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, team_id, scopes,
                          rate_limit_per_minute, rate_limit_per_day,
                          is_active, expires_at, revoked_at
                   FROM api_keys WHERE key_hash = %s""",
                (key_hash,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        (key_id, user_id, team_id, scopes,
         rl_min, rl_day, is_active, expires_at, revoked_at) = row

        if not is_active or revoked_at is not None:
            return None

        if expires_at is not None:
            from datetime import datetime, timezone
            if expires_at < datetime.now(timezone.utc):
                return None

        # レート制限カウンタ更新（既存 SQL 関数を使用）
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_api_key_rate_limit_status(%s, 'minute')",
                (key_id,),
            )
            count, limit, _, remaining = cur.fetchone()

        if remaining <= 0:
            raise RateLimited("API key rate limit exceeded (per minute)")

        # カウント増加
        with conn.cursor() as cur:
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'minute')",
                (key_id,),
            )
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'day')",
                (key_id,),
            )
        conn.commit()

        # last_used_at 更新（既存 SQL 関数）
        with conn.cursor() as cur:
            cur.execute("SELECT update_api_key_last_used(%s)", (key_id,))
        conn.commit()

        return AuthContext.from_api_key({
            "id": key_id, "user_id": user_id, "team_id": team_id,
            "scopes": scopes,
        })


async def log_api_key_request(
    api_key_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """API キー使用ログを記録（サンプリング適用）。"""
    from lib.config import get_settings
    settings = get_settings()
    sample_rate = settings.api_key_log_sample_rate
    if sample_rate < 1.0:
        import random
        if random.random() > sample_rate:
            return  # サンプル対象外

    await asyncio.to_thread(
        _log_sync, api_key_id, endpoint, method, status_code,
        response_time_ms, ip, user_agent,
    )


def _log_sync(api_key_id, endpoint, method, status_code, response_time_ms, ip, user_agent):
    from lib.database import get_connection_context
    with get_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT log_api_key_usage(%s, %s, %s, %s, %s, %s, %s)",
                (api_key_id, endpoint, method, status_code,
                 response_time_ms, ip, user_agent),
            )
        conn.commit()
```

- [ ] **Step 4: AuthContext を auth/__init__.py に追加**

`api/lib/auth/__init__.py` に以下を追加:

```python
from .context import AuthContext
from .api_key_auth import validate_api_key, API_KEY_PREFIX, log_api_key_request


async def get_auth_context_optional(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[AuthContext]:
    """JWT または API キーで認証。未認証なら None。"""
    if not authorization:
        return None
    token = extract_token_from_header(authorization)
    if not token:
        return None

    # API キー判別
    if token.startswith(API_KEY_PREFIX):
        try:
            return await validate_api_key(token)
        except RateLimited:
            raise HTTPException(429, "API key rate limit exceeded")

    # JWT パス
    result = await get_auth_provider().verify_access_token(token)
    if result.is_authenticated and result.user:
        return AuthContext.from_jwt_user(result.user)
    return None


async def require_auth_context(
    authorization: Annotated[Optional[str], Header()] = None,
) -> AuthContext:
    """JWT または API キーで認証必須。"""
    ctx = await get_auth_context_optional(authorization)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


# __all__ に追加
__all__ += ["AuthContext", "get_auth_context_optional", "require_auth_context"]
```

- [ ] **Step 5: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_api_key_auth.py -v
```

- [ ] **Step 6: コミット**

```bash
git add api/lib/auth/api_key_auth.py api/lib/auth/__init__.py api/tests/test_auth/test_api_key_auth.py
git commit -m "feat(auth): add API key validation with AuthContext + rate limiting"
```

### Task 3.3: タイル認可ヘルパ `check_tileset_access_v2`

**Files:**
- Modify: `api/lib/auth/__init__.py` (関数追加)
- Create: `api/tests/test_auth/test_tile_access_v2.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_tile_access_v2.py`:

```python
"""Tests for check_tileset_access_v2 / get_tileset_with_access_check_v2."""
import pytest
import uuid
from lib.auth import check_tileset_access_v2, AuthContext


@pytest.fixture
def setup_tileset(db_conn, clean_auth_tables):
    """テスト用タイルセットを作成"""
    owner_id = str(uuid.uuid4())

    def _create(is_public=False):
        tid = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'test', 'vector', 'pbf', %s, %s)""",
                (tid, owner_id, is_public),
            )
        db_conn.commit()
        return tid, owner_id

    return _create


class TestCheckTilesetAccessV2:
    @pytest.mark.asyncio
    async def test_public_allows_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=True)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await check_tileset_access_v2(db_conn, row, None) is True

    @pytest.mark.asyncio
    async def test_private_denies_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await check_tileset_access_v2(db_conn, row, None) is False

    @pytest.mark.asyncio
    async def test_owner_allowed(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, scopes=["read", "write", "admin"])
        assert await check_tileset_access_v2(db_conn, row, ctx) is True

    @pytest.mark.asyncio
    async def test_non_owner_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id="other-user", scopes=["read"])
        assert await check_tileset_access_v2(db_conn, row, ctx) is False

    @pytest.mark.asyncio
    async def test_api_key_no_read_scope_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, is_api_key=True, scopes=[])  # 空スコープ
        assert await check_tileset_access_v2(db_conn, row, ctx) is False
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_tile_access_v2.py -v
```

- [ ] **Step 3: 実装追加**

`api/lib/auth/__init__.py` に追加:

```python
async def check_tileset_access_v2(conn, tileset: dict, ctx: Optional[AuthContext]) -> bool:
    """タイルセットアクセス判定。

    ルール:
    1. 公開タイルセット → 誰でも可
    2. 認証なし → 不可
    3. read スコープなし → 不可
    4. オーナー → 可
    5. API キー（チーム紐付け）+ team_tilesets で共有 → 可
    6. JWT ユーザー + 所属チーム経由で共有 → 可
    """
    import asyncio

    if tileset.get("is_public"):
        return True
    if ctx is None:
        return False
    if not ctx.has_scope("read"):
        return False

    owner_id = tileset.get("user_id")
    if owner_id and ctx.user_id == str(owner_id):
        return True

    tileset_id = str(tileset["id"])

    if ctx.is_api_key:
        if ctx.team_id is None:
            return False
        return await asyncio.to_thread(_is_tileset_shared_with_team, conn, tileset_id, ctx.team_id)

    # JWT ユーザー: 所属する全チームを横断
    return await asyncio.to_thread(_user_has_team_access, conn, ctx.user_id, tileset_id)


def _is_tileset_shared_with_team(conn, tileset_id: str, team_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM team_tilesets WHERE team_id = %s AND tileset_id = %s LIMIT 1",
            (team_id, tileset_id),
        )
        return cur.fetchone() is not None


def _user_has_team_access(conn, user_id: str, tileset_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT 1 FROM team_members tm
               JOIN team_tilesets tt ON tm.team_id = tt.team_id
              WHERE tm.user_id = %s AND tt.tileset_id = %s
              LIMIT 1""",
            (user_id, tileset_id),
        )
        return cur.fetchone() is not None


# __all__ に追加
__all__ += ["check_tileset_access_v2"]
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_tile_access_v2.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/auth/__init__.py api/tests/test_auth/test_tile_access_v2.py
git commit -m "feat(auth): add check_tileset_access_v2 with team-based authorization"
```

---

## Phase 4: ルーターとミドルウェア

### Task 4.1: TwoTierCORSMiddleware

**Files:**
- Create: `api/lib/cors_middleware.py`
- Create: `api/tests/test_auth/test_cors_middleware.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_cors_middleware.py`:

```python
"""Tests for TwoTierCORSMiddleware."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.cors_middleware import TwoTierCORSMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(TwoTierCORSMiddleware, strict_origins=["http://allowed.com"])

    @app.get("/api/auth/test")
    async def auth_test():
        return {"ok": True}

    @app.get("/api/tiles/test")
    async def tiles_test():
        return {"ok": True}

    @app.get("/api/other")
    async def other():
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestStrictForAuth:
    def test_auth_endpoint_disallows_foreign_origin_credentials(self, client):
        # /api/auth/* は明示 origin リスト + credentials=true
        res = client.get("/api/auth/test", headers={"Origin": "http://attacker.com"})
        # origin がリストにないので Access-Control-Allow-Origin ヘッダなし
        assert res.headers.get("access-control-allow-origin") != "*"

    def test_auth_endpoint_allows_listed_origin(self, client):
        res = client.get("/api/auth/test", headers={"Origin": "http://allowed.com"})
        assert res.headers.get("access-control-allow-origin") == "http://allowed.com"
        assert res.headers.get("access-control-allow-credentials") == "true"


class TestPermissiveForOthers:
    def test_tiles_allow_any_origin(self, client):
        res = client.get("/api/tiles/test", headers={"Origin": "http://anywhere.com"})
        assert res.headers.get("access-control-allow-origin") == "*"

    def test_other_endpoints_also_permissive(self, client):
        res = client.get("/api/other", headers={"Origin": "http://anywhere.com"})
        assert res.headers.get("access-control-allow-origin") == "*"


class TestPathBoundary:
    def test_similar_path_not_treated_as_auth(self, client):
        # /api/auth-misuse は /api/auth/ ではない
        @client.app.get("/api/auth-misuse")
        async def fake():
            return {}

        res = client.get("/api/auth-misuse", headers={"Origin": "http://anywhere.com"})
        # permissive モード扱い
        assert res.headers.get("access-control-allow-origin") == "*"
```

- [ ] **Step 2: 失敗確認**

```bash
cd api && uv run pytest tests/test_auth/test_cors_middleware.py -v
```

- [ ] **Step 3: 実装**

`api/lib/cors_middleware.py`:

```python
"""TwoTierCORSMiddleware - パス別に CORS ポリシーを切り替える。

/api/auth/* → strict（allow_origins 指定 + allow_credentials=true）
それ以外    → permissive（allow_origins=* + allow_credentials=false）
"""
from typing import Sequence

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


AUTH_PATH_PREFIX = "/api/auth/"


class TwoTierCORSMiddleware:
    """2 つの CORS 設定を path で切り替える ASGI ミドルウェア。"""

    def __init__(self, app: ASGIApp, strict_origins: Sequence[str]):
        self._strict = CORSMiddleware(
            app,
            allow_origins=list(strict_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._public = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._strict(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(AUTH_PATH_PREFIX):
            await self._strict(scope, receive, send)
        else:
            await self._public(scope, receive, send)
```

- [ ] **Step 4: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_cors_middleware.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/cors_middleware.py api/tests/test_auth/test_cors_middleware.py
git commit -m "feat(api): add TwoTierCORSMiddleware for path-based CORS"
```

### Task 4.2: `routers/auth.py` (10 endpoints)

**Files:**
- Create: `api/lib/routers/auth.py`
- Create: `api/tests/test_routers/__init__.py`
- Create: `api/tests/test_routers/test_auth_routes.py`

このタスクは大きいので、エンドポイントごとに sub-task に分けて TDD する。

- [ ] **Step 1: 共通スケルトン作成**

`api/lib/routers/auth.py` 初版（空のルーター）:

```python
"""認証関連エンドポイント。"""
from datetime import datetime
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from lib.auth import (
    User, AuthContext, AuthError,
    InvalidCredentials, RateLimited, InvalidToken,
    UserAlreadyExists, UserNotFound, WeakPassword, ProviderError,
    require_auth, get_auth_provider,
)
from lib.config import get_settings
from lib.database import get_connection


router = APIRouter(prefix="/api/auth", tags=["auth"])


# === エラー翻訳 ===

ERROR_MAP = {
    InvalidCredentials: 401,
    RateLimited: 429,
    InvalidToken: 401,
    UserAlreadyExists: 409,
    UserNotFound: 404,
    WeakPassword: 400,
    ProviderError: 502,
}


def _translate(e: AuthError) -> HTTPException:
    code = ERROR_MAP.get(type(e), 500)
    return HTTPException(status_code=code, detail=str(e))


# === Cookie ヘルパ ===

REFRESH_COOKIE_NAME = "geo_base_refresh"
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/auth",
        domain=settings.cookie_domain or None,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth",
        domain=settings.cookie_domain or None,
    )


def _check_origin(request: Request) -> None:
    """state-changing endpoint で Origin ヘッダ検証"""
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(403, "Origin not allowed")
```

- [ ] **Step 2: テストファイル枠組み**

`api/tests/test_routers/test_auth_routes.py` 初版:

```python
"""Tests for /api/auth/* routes."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(local_auth_settings, db_conn, clean_auth_tables):
    """ローカル認証モードの API client"""
    from lib.main import app
    return TestClient(app)


@pytest.fixture
def local_auth_settings(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-" + "x" * 50)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("EMAIL_BACKEND", "null")
    monkeypatch.setenv("CORS_ORIGINS", '["http://testserver"]')
    monkeypatch.setenv("INVITATION_BASE_URL", "http://testserver")
    from lib.config import get_settings
    from lib.auth import get_auth_provider
    get_settings.cache_clear()
    get_auth_provider.cache_clear()


@pytest.fixture
def existing_user(client):
    res = client.post("/api/auth/_test_create_user", json={
        "email": "alice@test.com", "password": "ValidPass123", "name": "Alice",
    })
    # _test_create_user は実装後に追加されないので、CLI 経由 or 直接 DB INSERT で対応
    # → conftest フィクスチャで作成するのが正しい
```

注: `existing_user` フィクスチャは Task 4.5（conftest 拡充）で正式に追加。Phase 4 のテストは順次追加。

- [ ] **Step 3: POST /api/auth/login 実装**

`api/lib/routers/auth.py` に追加:

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
):
    """email + password でログイン。"""
    provider = get_auth_provider()
    try:
        pair = await provider.authenticate(
            body.email, body.password,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        raise _translate(e)

    user = await provider.get_user_by_email(body.email)
    _set_refresh_cookie(response, pair.refresh_token)
    return LoginResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
    )
```

テスト追加（test_auth_routes.py）:

```python
class TestLogin:
    def test_login_success(self, client, db_conn, clean_auth_tables):
        # ユーザー作成（直接 DB 経由）
        from lib.auth.providers.local import LocalAuthProvider
        import asyncio
        provider = LocalAuthProvider()
        asyncio.get_event_loop().run_until_complete(
            provider.create_user("alice@test.com", "ValidPass123", name="Alice")
        )

        res = client.post("/api/auth/login", json={
            "email": "alice@test.com", "password": "ValidPass123",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["access_token"]
        assert data["expires_in"] == 900
        assert data["user"]["email"] == "alice@test.com"
        # Set-Cookie がある
        assert "geo_base_refresh" in res.headers.get("set-cookie", "")

    def test_login_invalid_credentials(self, client, db_conn, clean_auth_tables):
        res = client.post("/api/auth/login", json={
            "email": "nobody@test.com", "password": "WrongPass",
        })
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["detail"]
```

- [ ] **Step 4: 残り 9 endpoint を順次追加**

スペック §7.2 の各エンドポイント仕様に従って実装。各エンドポイントごとに以下のサイクル:

- テスト書く（パス・エラー両方）
- 失敗確認
- 実装
- 成功確認

実装すべきエンドポイント（順序は依存関係に従う）:

1. ✅ `POST /login` （上記で完了）
2. `POST /refresh` — Cookie からトークン取得 → provider.refresh_tokens → Cookie 更新
3. `POST /logout` — Cookie からトークン → provider.revoke_refresh_token → Cookie 削除
4. `GET /me` — require_auth + provider.get_user_by_id（または JWT クレームから直接）
5. `PATCH /me` — require_auth + provider.update_user
6. `POST /me/password` — require_auth + 現在のパスワード検証 + update_password + revoke_all_user_tokens
7. `POST /password-reset/request` — provider.request_password_reset
8. `POST /password-reset/confirm` — provider.confirm_password_reset
9. `GET /invitations/{token}` — team_invitations から情報を返す
10. `POST /accept-invitation` — トランザクションで provider.create_user + team_members 追加 + invitation 更新

各 endpoint の実装スケルトンは以下（簡略版・エラーハンドリングと Origin チェックは適宜）:

```python
class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: Request, response: Response):
    _check_origin(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(401, "No refresh token")
    try:
        pair = await get_auth_provider().refresh_tokens(
            refresh_token,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        _clear_refresh_cookie(response)
        raise _translate(e)

    # ユーザー情報取得
    from lib.auth.jwt_utils import decode_access_token
    settings = get_settings()
    claims = decode_access_token(
        pair.access_token,
        secret=settings.effective_jwt_secret,
        audience=settings.jwt_audience,
    )
    user_id = claims["sub"]
    user = await get_auth_provider().get_user_by_id(user_id)
    _set_refresh_cookie(response, pair.refresh_token)
    return RefreshResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
    )


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    _check_origin(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            await get_auth_provider().revoke_refresh_token(refresh_token)
        except AuthError:
            pass
    _clear_refresh_cookie(response)


@router.get("/me", response_model=User)
async def get_me(user: User = Depends(require_auth)):
    return user


class UpdateMeRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    user_metadata: Optional[dict] = None


@router.patch("/me", response_model=User)
async def update_me(body: UpdateMeRequest, user: User = Depends(require_auth)):
    try:
        return await get_auth_provider().update_user(
            user.id, name=body.name, email=body.email, user_metadata=body.user_metadata,
        )
    except AuthError as e:
        raise _translate(e)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.post("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(require_auth),
):
    provider = get_auth_provider()
    # 現パスワード検証: authenticate でログイン試行
    try:
        await provider.authenticate(user.email, body.current_password)
    except AuthError:
        raise HTTPException(401, "Invalid current password")
    try:
        await provider.update_password(user.id, body.new_password)
    except AuthError as e:
        raise _translate(e)

    # 全 refresh token を失効（DB 直叩きでも provider 経由でも）
    from lib.auth.tokens import revoke_all_user_tokens
    from lib.database import get_connection_context
    with get_connection_context() as conn:
        revoke_all_user_tokens(conn, user.id, reason="password_changed")


class PasswordResetRequest(BaseModel):
    email: EmailStr


@router.post("/password-reset/request", status_code=204)
async def password_reset_request(body: PasswordResetRequest, request: Request):
    try:
        await get_auth_provider().request_password_reset(
            body.email,
            ip=request.client.host if request.client else None,
        )
    except AuthError:
        pass  # 情報漏洩防止のため常に 204


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)


@router.post("/password-reset/confirm", status_code=204)
async def password_reset_confirm(body: PasswordResetConfirm):
    try:
        await get_auth_provider().confirm_password_reset(body.token, body.new_password)
    except AuthError as e:
        raise _translate(e)


class InvitationInfoResponse(BaseModel):
    team_id: str
    team_name: str
    team_slug: str
    role: str
    email: str
    inviter_name: Optional[str] = None
    expires_at: datetime
    has_existing_account: bool


@router.get("/invitations/{token}", response_model=InvitationInfoResponse)
async def get_invitation(token: str, conn=Depends(get_connection)):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT i.team_id, t.name, t.slug, i.role, i.email, i.expires_at, i.status,
                      u_inviter.name AS inviter_name
               FROM team_invitations i
               JOIN teams t ON i.team_id = t.id
               LEFT JOIN users u_inviter ON u_inviter.id = i.invited_by
               WHERE i.token = %s""",
            (token,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Invitation not found")

    team_id, team_name, team_slug, role, email, expires_at, status_, inviter_name = row
    if status_ != "pending":
        raise HTTPException(404, f"Invitation is {status_}")
    if expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
        raise HTTPException(404, "Invitation expired")

    existing = await get_auth_provider().get_user_by_email(email)
    return InvitationInfoResponse(
        team_id=str(team_id), team_name=team_name, team_slug=team_slug,
        role=role, email=email, inviter_name=inviter_name,
        expires_at=expires_at,
        has_existing_account=existing is not None,
    )


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)
    name: Optional[str] = Field(None, max_length=255)


class AcceptInvitationResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User
    team_member: dict


@router.post("/accept-invitation", response_model=AcceptInvitationResponse, status_code=201)
async def accept_invitation(
    body: AcceptInvitationRequest,
    response: Response,
    request: Request,
    conn=Depends(get_connection),
):
    # 招待検証
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, team_id, email, role, expires_at, status
               FROM team_invitations WHERE token = %s FOR UPDATE""",
            (body.token,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(400, "Invalid invitation token")
    inv_id, team_id, email, role, expires_at, status_ = row

    if status_ != "pending":
        raise HTTPException(400, f"Invitation is {status_}")
    if expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
        raise HTTPException(400, "Invitation has expired")

    provider = get_auth_provider()

    # 既存ユーザーチェック
    existing = await provider.get_user_by_email(email)
    if existing is not None:
        raise HTTPException(409, "An account with this email already exists. Please log in and accept via /api/teams/invitations/accept")

    # ユーザー作成
    try:
        user = await provider.create_user(
            email=email, password=body.password, name=body.name,
            email_verified=True,
        )
    except AuthError as e:
        raise _translate(e)

    # team_members 追加 + 招待を accepted に更新（同一トランザクション）
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO team_members (team_id, user_id, role)
               VALUES (%s, %s, %s)""",
            (team_id, user.id, role),
        )
        cur.execute(
            "UPDATE team_invitations SET status = 'accepted', accepted_at = NOW() WHERE id = %s",
            (inv_id,),
        )
    conn.commit()

    # ログイン状態にする
    pair = await provider.authenticate(
        email, body.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, pair.refresh_token)
    return AcceptInvitationResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
        team_member={"team_id": str(team_id), "role": role},
    )
```

各エンドポイントごとに 1 つ実装 → テスト追加 → 実行 → コミットを繰り返す。

- [ ] **Step 5: 各エンドポイントのテストを追加**

`api/tests/test_routers/test_auth_routes.py` に各エンドポイント用のテストクラスを追加。各クラス最低 4 ケース（成功/不正/権限不足/エッジケース）。

- [ ] **Step 6: 全 endpoint テスト実行**

```bash
cd api && uv run pytest tests/test_routers/test_auth_routes.py -v
```

- [ ] **Step 7: コミット（endpoint ごとに分けて or 一括）**

```bash
git add api/lib/routers/auth.py api/tests/test_routers/
git commit -m "feat(api): add /api/auth/* routes (login, refresh, logout, me, password, reset, invitation)"
```

### Task 4.3: `main.py` の middleware 差し替え + auth_router 追加

**Files:**
- Modify: `api/lib/main.py`

- [ ] **Step 1: 既存 main.py のバックアップ確認**

```bash
ls api/lib/main.py.backup 2>/dev/null && echo "backup exists"
```

- [ ] **Step 2: main.py 修正**

`api/lib/main.py`:

```python
# 既存 import に追加
from lib.cors_middleware import TwoTierCORSMiddleware
from lib.routers.auth import router as auth_router

# 既存の app.add_middleware(CORSMiddleware, ...) を以下に置き換え:

# settings = get_settings()
# 変更前:
#   app.add_middleware(
#       CORSMiddleware,
#       allow_origins=["*"],
#       allow_credentials=False,
#       ...
#   )
# 変更後:
app.add_middleware(
    TwoTierCORSMiddleware,
    strict_origins=settings.cors_origins,
)

# Include Routers にも追加（auth_router を最初に追加）
app.include_router(auth_router)
# 既存の include_router 群はそのまま
```

- [ ] **Step 3: 起動確認**

```bash
cd api && uv run uvicorn lib.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/health
curl -s -i http://localhost:8000/api/tiles/raster/dummy/0/0/0.png 2>&1 | head -5
kill %1
```

期待: 起動成功、tile エンドポイントで CORS ヘッダ `Access-Control-Allow-Origin: *` が返る。

- [ ] **Step 4: コミット**

```bash
git add api/lib/main.py
git commit -m "feat(api): swap CORSMiddleware to TwoTierCORSMiddleware, add auth router"
```

### Task 4.4: タイル系ルーターを AuthContext 対応に

**Files:**
- Modify: `api/lib/routers/tiles/dynamic.py`
- Modify: `api/lib/routers/tiles/pmtiles.py`
- Modify: `api/lib/routers/tiles/raster.py`
- Modify: `api/lib/routers/tiles/mbtiles.py`
- Modify: `api/lib/routers/tilesets.py`（tilejson エンドポイント）
- Create: `api/tests/test_routers/test_tile_access.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_routers/test_tile_access.py`:

```python
"""Tests for tile authorization with JWT and API keys."""
import pytest
from fastapi.testclient import TestClient


# 詳細なテストケースは既存の test_tile_access_v2.py のパターンを応用
# ここではエンドツーエンドの API レスポンスを確認

class TestPublicTileAccess:
    def test_anonymous_can_access_public_tile(self, client, public_tileset):
        # 公開タイルセットには認証なしでアクセス可
        res = client.get(f"/api/tilesets/{public_tileset['id']}/tilejson.json")
        assert res.status_code == 200


class TestPrivateTileAccess:
    def test_anonymous_denied(self, client, private_tileset):
        res = client.get(f"/api/tilesets/{private_tileset['id']}/tilejson.json")
        assert res.status_code == 401

    def test_owner_jwt_allowed(self, client, private_tileset, owner_jwt):
        res = client.get(
            f"/api/tilesets/{private_tileset['id']}/tilejson.json",
            headers={"Authorization": f"Bearer {owner_jwt}"},
        )
        assert res.status_code == 200

    def test_api_key_with_team_access(self, client, private_tileset, api_key_with_team):
        res = client.get(
            f"/api/tilesets/{private_tileset['id']}/tilejson.json",
            headers={"Authorization": f"Bearer {api_key_with_team}"},
        )
        # private_tileset が team に share されていれば 200、されてなければ 403
        # フィクスチャに依存
```

注: `public_tileset`, `private_tileset`, `owner_jwt`, `api_key_with_team` フィクスチャは Task 4.5 で conftest に追加。

- [ ] **Step 2: タイル系各ルーターを修正**

各ファイルで以下のパターン適用:

```python
# 修正前:
from lib.auth import User, get_current_user, get_tileset_with_access_check

@router.get("/...")
async def some_endpoint(
    ...,
    current_user: Optional[User] = Depends(get_current_user),
    conn=Depends(get_connection),
):
    tileset = await get_tileset_with_access_check(tileset_id, conn, current_user)
    ...
```

```python
# 修正後:
from lib.auth import (
    AuthContext, get_auth_context_optional, check_tileset_access_v2,
)

@router.get("/...")
async def some_endpoint(
    ...,
    auth: Optional[AuthContext] = Depends(get_auth_context_optional),
    conn=Depends(get_connection),
):
    # tileset 取得
    with conn.cursor() as cur:
        cur.execute("SELECT id, user_id, is_public, ... FROM tilesets WHERE id = %s", (tileset_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Tileset not found: {tileset_id}")
    tileset = dict(zip([d[0] for d in cur.description], row))

    if not await check_tileset_access_v2(conn, tileset, auth):
        if auth is None:
            raise HTTPException(401, "Authentication required")
        raise HTTPException(403, "Access denied")
    ...
```

各ファイル（dynamic.py, pmtiles.py, raster.py, mbtiles.py, tilesets.py）でこのパターンを適用。詳細はファイルごとに既存実装と照らし合わせて慎重に対応。

- [ ] **Step 3: 既存テストの動作確認**

```bash
cd api && uv run pytest tests/ -v --tb=short -x 2>&1 | tail -30
```

期待: 既存タイル関連テスト（あれば）が引き続き通る。

- [ ] **Step 4: コミット**

```bash
git add api/lib/routers/tiles/ api/lib/routers/tilesets.py
git commit -m "feat(tiles): use AuthContext + check_tileset_access_v2 for JWT/API key authorization"
```

### Task 4.5: conftest.py のテストフィクスチャ拡充

**Files:**
- Modify: `api/tests/conftest.py`

- [ ] **Step 1: フィクスチャ追加**

`api/tests/conftest.py` に追加:

```python
@pytest.fixture
def null_email_backend(monkeypatch):
    """get_email_backend() を NullEmailBackend に差し替え。"""
    from lib.auth.email_backends import NullEmailBackend, get_email_backend
    backend = NullEmailBackend()
    monkeypatch.setattr("lib.auth.email_backends.get_email_backend", lambda: backend)
    get_email_backend.cache_clear()
    return backend


@pytest.fixture
def local_auth_settings(monkeypatch):
    """テスト用 local 認証設定オーバーライド。"""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-" + "x" * 40)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("JWT_ISSUER", "geo-base-test")
    monkeypatch.setenv("EMAIL_BACKEND", "null")
    monkeypatch.setenv("INVITATION_BASE_URL", "http://testserver")
    monkeypatch.setenv("CORS_ORIGINS", '["http://testserver"]')

    from lib.config import get_settings
    from lib.auth import get_auth_provider
    from lib.auth.email_backends import get_email_backend
    get_settings.cache_clear()
    get_auth_provider.cache_clear()
    get_email_backend.cache_clear()
    yield
    get_settings.cache_clear()
    get_auth_provider.cache_clear()
    get_email_backend.cache_clear()


@pytest.fixture
def make_user(db_conn, clean_auth_tables, local_auth_settings):
    """ローカル DB にユーザーを作成するファクトリ。"""
    import uuid as uuid_lib
    import asyncio
    from lib.auth.providers.local import LocalAuthProvider

    def _make(email=None, password="ValidPass123", name="Test User"):
        email = email or f"u-{uuid_lib.uuid4().hex[:8]}@example.test"
        provider = LocalAuthProvider()
        return asyncio.get_event_loop().run_until_complete(
            provider.create_user(email, password, name=name, email_verified=True)
        )

    return _make


@pytest.fixture
def make_team(db_conn, make_user):
    """チーム作成ファクトリ。"""
    import uuid as uuid_lib

    def _make(owner=None, name=None):
        owner = owner or make_user()
        team_name = name or f"team-{uuid_lib.uuid4().hex[:6]}"
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (name, slug, owner_id) VALUES (%s, %s, %s) RETURNING id",
                (team_name, team_name.lower(), owner.id),
            )
            team_id = str(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO team_members (team_id, user_id, role) VALUES (%s, %s, 'owner')",
                (team_id, owner.id),
            )
        db_conn.commit()
        return {"id": team_id, "name": team_name, "owner": owner}

    return _make


@pytest.fixture
def make_api_key(db_conn, make_user):
    """API キー発行ファクトリ。"""
    import secrets, hashlib

    def _make(user=None, team_id=None, scopes=None):
        user = user or make_user()
        scopes = scopes or ["read"]
        random_part = secrets.token_urlsafe(32)
        full_key = f"gb_test_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        prefix = full_key[:12]
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_keys (name, prefix, key_hash, user_id, team_id, scopes)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                ("test", prefix, key_hash, user.id, team_id, scopes),
            )
            key_id = str(cur.fetchone()[0])
        db_conn.commit()
        return {"key": full_key, "id": key_id, "user": user}

    return _make


@pytest.fixture
def public_tileset(db_conn, make_user):
    """公開タイルセット"""
    import uuid as uuid_lib
    user = make_user()
    tid = str(uuid_lib.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
               VALUES (%s, 'public', 'vector', 'pbf', %s, TRUE)""",
            (tid, user.id),
        )
    db_conn.commit()
    return {"id": tid, "owner": user}


@pytest.fixture
def private_tileset(db_conn, make_user):
    """非公開タイルセット"""
    import uuid as uuid_lib
    user = make_user()
    tid = str(uuid_lib.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
               VALUES (%s, 'private', 'vector', 'pbf', %s, FALSE)""",
            (tid, user.id),
        )
    db_conn.commit()
    return {"id": tid, "owner": user}
```

- [ ] **Step 2: 既存テスト動作確認**

```bash
cd api && uv run pytest tests/ -v --tb=short 2>&1 | tail -20
```

期待: 既存テスト + 新規テストが全て通る。

- [ ] **Step 3: コミット**

```bash
git add api/tests/conftest.py
git commit -m "test(auth): add fixtures for users, teams, api keys, tilesets"
```

### Task 4.6: 既存ルーターの調整

**Files:**
- Modify: `api/lib/routers/health.py`（/api/auth/me 削除）
- Modify: `api/lib/routers/teams.py`（招待メール送信統合 + email 検証）

#### Task 4.6a: health.py の auth エンドポイント削除

- [ ] **Step 1: 確認**

```bash
cd api && grep -n "auth" lib/routers/health.py
```

- [ ] **Step 2: /api/auth/* エンドポイントを health.py から削除**

`api/lib/routers/health.py` から `/api/auth/me`, `/api/auth/status` 等の関数を削除（残すのは `/api/health`, `/api/health/db` のみ）。

- [ ] **Step 3: 動作確認**

```bash
cd api && uv run uvicorn lib.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/auth/me  # 新ルーター経由（401 返るはず）
kill %1
```

期待: 401 が返る（新 routers/auth.py の require_auth が機能している）。

- [ ] **Step 4: コミット**

```bash
git add api/lib/routers/health.py
git commit -m "refactor(api): remove auth endpoints from health router (now in routers/auth.py)"
```

#### Task 4.6b: teams.py の招待メール送信

- [ ] **Step 1: テスト追加**

`api/tests/test_teams.py` に追加（既存ファイル）:

```python
class TestInvitationEmail:
    def test_invitation_creation_sends_email(
        self, client, null_email_backend, make_team, owner_jwt
    ):
        team = make_team()
        # ヘッダで JWT を渡してログイン状態にする想定（owner_jwt は別フィクスチャ）
        res = client.post(
            f"/api/teams/{team['id']}/invitations",
            json={"email": "newbie@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {owner_jwt}"},
        )
        assert res.status_code == 201
        assert len(null_email_backend.sent) == 1
        sent = null_email_backend.sent[0]
        assert sent["to"] == "newbie@test.com"
        assert team["name"] in sent["subject"]
        assert "/accept-invitation?token=" in sent["body"]
```

- [ ] **Step 2: teams.py に招待メール送信統合**

`api/lib/routers/teams.py` の `create_team_invitation` 関数の最後（commit 後）に追加:

```python
# 招待メール送信
from lib.auth.email_backends import get_email_backend
from lib.auth.email_backends.templates import render_invitation_email

accept_url = f"{settings.invitation_base_url}/accept-invitation?token={token}"
inviter_name = user.name or user.email or "Unknown"
subject, body = render_invitation_email(
    team_name=team['name'],
    inviter_name=inviter_name,
    accept_url=accept_url,
    expires_at=expires_at,
)
try:
    await get_email_backend().send(invitation_data.email, subject, body)
except Exception as e:
    logger.error(f"Failed to send invitation email: {e}")
    # メール送信失敗は招待作成自体を失敗させない
```

`team` 変数（dict）を関数内で利用可能にするため、INSERT 後に SELECT で取得する処理を追加（既存実装に応じて調整）。

- [ ] **Step 3: invitation accept で email 一致検証追加**

`api/lib/routers/teams.py` の `accept_team_invitation` 関数に以下を追加:

```python
# 既存: invitation の status, expires_at チェック後

# 追加: email 一致検証
if user.email and user.email.lower() != email.lower():
    raise HTTPException(403, "Invitation email does not match your account email")
```

- [ ] **Step 4: 動作確認**

```bash
cd api && uv run pytest tests/test_teams.py -v
```

- [ ] **Step 5: コミット**

```bash
git add api/lib/routers/teams.py api/tests/test_teams.py
git commit -m "feat(teams): send invitation email on creation, verify email match on accept"
```

---


## Phase 5: CLI と設定検証

### Task 5.1: 設定検証 (`config.py`)

**Files:**
- Modify: `api/lib/config.py`
- Modify: `api/tests/test_auth/test_factory.py`（設定検証テスト追加）

- [ ] **Step 1: テスト追加**

`api/tests/test_auth/test_factory.py` に追加:

```python
class TestConfigValidation:
    def test_local_without_jwt_secret_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="JWT_SECRET"):
            get_settings()

    def test_supabase_without_url_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="SUPABASE_URL"):
            get_settings()

    def test_smtp_without_host_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        monkeypatch.setenv("EMAIL_BACKEND", "smtp")
        monkeypatch.delenv("SMTP_HOST", raising=False)
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="SMTP_HOST"):
            get_settings()

    def test_samesite_none_without_secure_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        monkeypatch.setenv("COOKIE_SAMESITE", "none")
        monkeypatch.setenv("COOKIE_SECURE", "false")
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="COOKIE_SECURE"):
            get_settings()
```

- [ ] **Step 2: `Settings` クラスにバリデーター追加**

`api/lib/config.py` の `Settings` クラスに追加:

```python
from pydantic import model_validator

# Settings クラス内に追加
@model_validator(mode='after')
def validate_auth_config(self) -> 'Settings':
    if self.auth_provider == "local":
        if not self.effective_jwt_secret:
            raise ValueError(
                "AUTH_PROVIDER=local requires JWT_SECRET (or SUPABASE_JWT_SECRET as fallback)"
            )
    elif self.auth_provider == "supabase":
        if not self.supabase_url:
            raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_URL")
        if not self.supabase_service_role_key:
            raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_SERVICE_ROLE_KEY")
        if not self.supabase_jwt_secret:
            raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_JWT_SECRET")
    else:
        raise ValueError(f"Unknown AUTH_PROVIDER: {self.auth_provider}")

    if self.email_backend == "smtp":
        if not self.smtp_host:
            raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST")
        if not self.smtp_from:
            raise ValueError("EMAIL_BACKEND=smtp requires SMTP_FROM")
    elif self.email_backend not in ("null", "console"):
        raise ValueError(f"Unknown EMAIL_BACKEND: {self.email_backend}")

    if self.cookie_samesite == "none" and not self.cookie_secure:
        raise ValueError(
            "COOKIE_SAMESITE=none requires COOKIE_SECURE=true (browser security requirement)"
        )

    return self
```

- [ ] **Step 3: 成功確認**

```bash
cd api && uv run pytest tests/test_auth/test_factory.py::TestConfigValidation -v
```

- [ ] **Step 4: コミット**

```bash
git add api/lib/config.py api/tests/test_auth/test_factory.py
git commit -m "feat(config): add fail-fast validation for auth provider settings"
```

### Task 5.2: CLI (`auth/cli.py`)

**Files:**
- Create: `api/lib/auth/cli.py`
- Create: `api/tests/test_auth/test_cli.py`

- [ ] **Step 1: テスト作成**

`api/tests/test_auth/test_cli.py`:

```python
"""Tests for auth CLI."""
import subprocess
import os
import pytest


class TestCli:
    def test_help_runs(self):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "--help"],
            cwd="api", env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "create-admin" in result.stdout

    def test_list_users_empty(self, db_conn, clean_auth_tables):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "list-users", "--json"],
            cwd="api", env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "[]" in result.stdout
```

注: 対話的なパスワード入力を含む `create-admin` のテストはサブプロセス + stdin 入力で書く。Phase 3 では smoke test のみ十分。

- [ ] **Step 2: 実装**

`api/lib/auth/cli.py`:

```python
"""auth CLI: python -m lib.auth.cli <command>"""
import argparse
import asyncio
import getpass
import json
import sys
from typing import Optional

from .errors import AuthError, UserAlreadyExists, WeakPassword


async def cmd_create_admin(args):
    from . import get_auth_provider
    provider = get_auth_provider()

    email = args.email
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Passwords do not match", file=sys.stderr)
        sys.exit(1)

    name = input("Name (optional): ").strip() or None

    try:
        user = await provider.create_user(
            email=email, password=password, name=name,
            email_verified=True,
            app_metadata={"role": "admin"},
        )
    except UserAlreadyExists:
        print(f"User with email {email} already exists", file=sys.stderr)
        sys.exit(1)
    except WeakPassword as e:
        print(f"Weak password: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Admin user created: {user.id}")
    print(f"   Email: {user.email}")


async def cmd_revoke_user_tokens(args):
    from .tokens import revoke_all_user_tokens
    from lib.database import get_connection_context

    with get_connection_context() as conn:
        count = revoke_all_user_tokens(conn, args.user_id, reason="admin_revocation")

    print(f"✅ Revoked {count} refresh tokens for user {args.user_id}")


async def cmd_cleanup_expired(args):
    from lib.database import get_connection_context

    with get_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cleanup_expired_refresh_tokens()")
            rt = cur.fetchone()[0]
            cur.execute("SELECT cleanup_old_login_attempts()")
            la = cur.fetchone()[0]
            cur.execute("SELECT cleanup_expired_password_reset_tokens()")
            pr = cur.fetchone()[0]
            cur.execute("SELECT expire_old_invitations()")
            inv = cur.fetchone()[0]
        conn.commit()

    print(f"✅ Cleanup complete:")
    print(f"   Refresh tokens removed:        {rt}")
    print(f"   Login attempts removed:        {la}")
    print(f"   Password reset tokens removed: {pr}")
    print(f"   Invitations expired:           {inv}")


async def cmd_reset_password(args):
    from . import get_auth_provider
    await get_auth_provider().request_password_reset(args.email)
    print(f"✅ Password reset email triggered for {args.email}")


async def cmd_list_users(args):
    from lib.database import get_connection_context

    with get_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, email, name, role, is_active,
                          email_verified_at, last_login_at, created_at
                   FROM users ORDER BY created_at DESC"""
            )
            rows = cur.fetchall()

    users = []
    for row in rows:
        users.append({
            "id": str(row[0]), "email": row[1], "name": row[2], "role": row[3],
            "is_active": row[4],
            "email_verified": row[5] is not None,
            "last_login_at": row[6].isoformat() if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
        })

    if args.json:
        print(json.dumps(users, indent=2, ensure_ascii=False))
    else:
        if not users:
            print("(no users)")
            return
        for u in users:
            verified = "✓" if u["email_verified"] else "✗"
            active = "✓" if u["is_active"] else "✗"
            print(f"{u['id']}  {u['email']:30s}  active={active} verified={verified}")


def main():
    parser = argparse.ArgumentParser(prog="lib.auth.cli", description="geo-base auth CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create-admin", help="Create initial admin user")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_create_admin)

    p = sub.add_parser("revoke-user-tokens", help="Revoke all refresh tokens for a user")
    p.add_argument("user_id")
    p.set_defaults(func=cmd_revoke_user_tokens)

    p = sub.add_parser("cleanup-expired", help="Cleanup expired tokens and old data")
    p.set_defaults(func=cmd_cleanup_expired)

    p = sub.add_parser("reset-password", help="Trigger password reset for a user")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_reset_password)

    p = sub.add_parser("list-users", help="List all users")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list_users)

    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: smoke test 実行**

```bash
cd api && uv run pytest tests/test_auth/test_cli.py -v
```

- [ ] **Step 4: 手動動作確認**

```bash
cd api
export AUTH_PROVIDER=local
export JWT_SECRET=$(openssl rand -base64 64)
uv run python -m lib.auth.cli --help
uv run python -m lib.auth.cli list-users --json
```

期待: ヘルプ表示 + 空のリスト `[]`

- [ ] **Step 5: コミット**

```bash
git add api/lib/auth/cli.py api/tests/test_auth/test_cli.py
git commit -m "feat(auth): add CLI for admin bootstrap, token revocation, cleanup"
```

---

## Phase 6: Admin UI

### Task 6.1: 型定義とエラー

**Files:**
- Create: `app/src/lib/auth/types.ts`
- Create: `app/src/lib/auth/errors.ts`

- [ ] **Step 1: 型定義作成**

`app/src/lib/auth/types.ts`:

```typescript
export interface User {
  id: string;
  email: string | null;
  role: string | null;
  name: string | null;
  email_verified: boolean;
  app_metadata?: Record<string, unknown> | null;
  user_metadata?: Record<string, unknown> | null;
}

export interface TokenPair {
  access_token: string;
  expires_in: number;
  token_type: string;
  user: User;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface InvitationInfo {
  team_id: string;
  team_name: string;
  team_slug: string;
  role: string;
  email: string;
  inviter_name: string | null;
  expires_at: string;
  has_existing_account: boolean;
}
```

- [ ] **Step 2: エラー定義作成**

`app/src/lib/auth/errors.ts`:

```typescript
export class AuthApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

export class InvalidCredentialsError extends AuthApiError {}
export class RateLimitedError extends AuthApiError {}
export class UnauthorizedError extends AuthApiError {}
export class WeakPasswordError extends AuthApiError {}
export class UserAlreadyExistsError extends AuthApiError {}

export async function parseAuthError(response: Response): Promise<AuthApiError> {
  let detail = "Authentication error";
  try {
    const data = await response.json();
    detail = data.detail || detail;
  } catch {
    // ignore
  }

  switch (response.status) {
    case 401:
      return new UnauthorizedError(401, detail);
    case 429:
      return new RateLimitedError(429, detail);
    case 400:
      if (detail.toLowerCase().includes("password")) {
        return new WeakPasswordError(400, detail);
      }
      return new AuthApiError(400, detail);
    case 409:
      return new UserAlreadyExistsError(409, detail);
    default:
      return new AuthApiError(response.status, detail);
  }
}
```

- [ ] **Step 3: コミット**

```bash
git add app/src/lib/auth/types.ts app/src/lib/auth/errors.ts
git commit -m "feat(ui): add auth types and errors"
```

### Task 6.2: AuthClient

**Files:**
- Create: `app/src/lib/auth/client.ts`

- [ ] **Step 1: 実装**

`app/src/lib/auth/client.ts`:

```typescript
import { User, TokenPair, AuthState, InvitationInfo } from "./types";
import { parseAuthError } from "./errors";


const API_URL = process.env.NEXT_PUBLIC_API_URL || "";


type Listener = (state: AuthState) => void;


class AuthClient {
  private accessToken: string | null = null;
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Set<Listener> = new Set();
  private state: AuthState = { user: null, isLoading: true, isAuthenticated: false };
  private refreshing: Promise<User | null> | null = null;

  async login(email: string, password: string): Promise<User> {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw await parseAuthError(res);
    const data: TokenPair = await res.json();
    this.setSession(data);
    return data.user;
  }

  async refresh(): Promise<User | null> {
    // 並行 refresh の重複防止
    if (this.refreshing) return this.refreshing;

    this.refreshing = this._doRefresh();
    try {
      return await this.refreshing;
    } finally {
      this.refreshing = null;
    }
  }

  private async _doRefresh(): Promise<User | null> {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      this.clearSession();
      return null;
    }
    const data: TokenPair = await res.json();
    this.setSession(data);
    return data.user;
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore network errors
    }
    this.clearSession();
  }

  async acceptInvitation(token: string, password: string, name: string): Promise<User> {
    const res = await fetch(`${API_URL}/api/auth/accept-invitation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ token, password, name }),
    });
    if (!res.ok) throw await parseAuthError(res);
    const data = await res.json();
    this.setSession(data);
    return data.user;
  }

  async getInvitationInfo(token: string): Promise<InvitationInfo> {
    const res = await fetch(`${API_URL}/api/auth/invitations/${token}`);
    if (!res.ok) throw await parseAuthError(res);
    return res.json();
  }

  async requestPasswordReset(email: string): Promise<void> {
    await fetch(`${API_URL}/api/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    if (!res.ok) throw await parseAuthError(res);
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  getState(): AuthState {
    return this.state;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setSession(data: TokenPair): void {
    this.accessToken = data.access_token;
    this.scheduleRefresh(data.expires_in);
    this.state = { user: data.user, isLoading: false, isAuthenticated: true };
    this.notify();
  }

  private clearSession(): void {
    this.accessToken = null;
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.state = { user: null, isLoading: false, isAuthenticated: false };
    this.notify();
  }

  private scheduleRefresh(expiresInSec: number): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    const refreshIn = Math.max((expiresInSec - 60) * 1000, 1000);
    this.refreshTimer = setTimeout(() => {
      this.refresh().catch(() => this.clearSession());
    }, refreshIn);
  }

  private notify(): void {
    this.listeners.forEach((l) => l(this.state));
  }
}


export const authClient = new AuthClient();
```

- [ ] **Step 2: コミット**

```bash
git add app/src/lib/auth/client.ts
git commit -m "feat(ui): add AuthClient singleton with token rotation and subscriptions"
```

### Task 6.3: React Context (AuthProvider)

**Files:**
- Create: `app/src/lib/auth/context.tsx`

- [ ] **Step 1: 実装**

`app/src/lib/auth/context.tsx`:

```typescript
"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authClient } from "./client";
import { AuthState } from "./types";


const AuthContext = createContext<AuthState>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
});


export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(authClient.getState());

  useEffect(() => {
    authClient.refresh().catch(() => { /* ignore */ });
    const unsub = authClient.subscribe(setState);
    return unsub;
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}


export function useAuth(): AuthState {
  return useContext(AuthContext);
}
```

- [ ] **Step 2: コミット**

```bash
git add app/src/lib/auth/context.tsx
git commit -m "feat(ui): add AuthProvider context and useAuth hook"
```

### Task 6.4: middleware.ts

**Files:**
- Create: `app/src/middleware.ts`

- [ ] **Step 1: 実装**

`app/src/middleware.ts`:

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";


const PROTECTED_PATHS = [
  "/tilesets", "/features", "/datasources",
  "/teams", "/api-keys", "/settings",
];

const AUTH_ONLY_PATHS = [
  "/login",
  "/password-reset/request",
  "/password-reset/confirm",
];


export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefresh = !!request.cookies.get("geo_base_refresh");

  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_ONLY_PATHS.includes(pathname);

  if (isProtected && !hasRefresh) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && hasRefresh) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}


export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 2: コミット**

```bash
git add app/src/middleware.ts
git commit -m "feat(ui): add middleware for route guards based on refresh cookie presence"
```

### Task 6.5: api.ts 更新

**Files:**
- Modify: `app/src/lib/api.ts`

- [ ] **Step 1: 既存 api.ts 確認**

```bash
head -50 app/src/lib/api.ts
```

- [ ] **Step 2: Authorization 自動付与 + 401 リトライ実装**

`app/src/lib/api.ts` の fetch ラッパー部分を以下に置換:

```typescript
import { authClient } from "./auth/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";


export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = authClient.getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  // 401 → 1 度だけ refresh して retry
  if (res.status === 401 && token) {
    const newUser = await authClient.refresh();
    if (newUser) {
      const newToken = authClient.getAccessToken();
      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
        res = await fetch(`${API_BASE_URL}${path}`, {
          ...options,
          headers,
          credentials: "include",
        });
      }
    }
  }

  return res;
}
```

既存の API 関数（`getTilesets`, `createFeature` 等）が直接 `fetch` を呼んでいる場合、`apiFetch` 経由に置換する。

- [ ] **Step 3: コミット**

```bash
git add app/src/lib/api.ts
git commit -m "feat(ui): integrate AuthClient token into apiFetch with 401 retry"
```

### Task 6.6: layout.tsx 更新（AuthProvider でラップ）

**Files:**
- Modify: `app/src/app/layout.tsx`

- [ ] **Step 1: layout.tsx 修正**

`app/src/app/layout.tsx` の `<body>` 内を `<AuthProvider>` でラップ:

```tsx
import { AuthProvider } from "@/lib/auth/context";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

既存の何らかの provider やレイアウトコンポーネントがあれば、その内側に AuthProvider を配置する。

- [ ] **Step 2: 起動確認**

```bash
cd app && npm run dev
```

ブラウザで http://localhost:3000 を開く。コンソールエラーがないか確認。

- [ ] **Step 3: コミット**

```bash
git add app/src/app/layout.tsx
git commit -m "feat(ui): wrap layout with AuthProvider"
```

### Task 6.7: 認証ページ（login, accept-invitation, password-reset, settings）

**Files:**
- Modify: `app/src/app/login/page.tsx`
- Create: `app/src/app/accept-invitation/page.tsx`
- Create: `app/src/app/password-reset/request/page.tsx`
- Create: `app/src/app/password-reset/confirm/page.tsx`
- Create: `app/src/app/settings/profile/page.tsx`
- Create: `app/src/app/settings/password/page.tsx`
- Create: `app/src/components/auth/login-form.tsx`
- Create: `app/src/components/auth/invitation-signup-form.tsx`
- Create: `app/src/components/auth/password-reset-form.tsx`

各ページは比較的シンプルな form なので、まとめて実装。詳細は既存の `app/src/app/login/page.tsx` のスタイルに合わせる。

- [ ] **Step 1: login/page.tsx を Supabase 抜きで再実装**

`app/src/app/login/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth/client";
import { AuthApiError } from "@/lib/auth/errors";


export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authClient.login(email, password);
      const next = params.get("next") || "/";
      router.push(next);
    } catch (err) {
      const msg = err instanceof AuthApiError ? err.detail : "Login failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">ログイン</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
        />
        <input
          type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="パスワード" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "ログイン"}
        </button>
        <a href="/password-reset/request" className="block text-center text-sm">
          パスワードをお忘れですか？
        </a>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: accept-invitation/page.tsx**

`app/src/app/accept-invitation/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth/client";
import { InvitationInfo } from "@/lib/auth/types";
import { AuthApiError } from "@/lib/auth/errors";


export default function AcceptInvitationPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");

  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Invalid invitation link");
      return;
    }
    authClient.getInvitationInfo(token)
      .then(setInfo)
      .catch((err) => setError(err instanceof AuthApiError ? err.detail : "Invitation not found"));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      await authClient.acceptInvitation(token, password, name);
      if (info) router.push(`/teams/${info.team_id}`);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.detail : "Failed to accept invitation");
    } finally {
      setLoading(false);
    }
  };

  if (error && !info) return <div className="container py-12"><p className="text-red-600">{error}</p></div>;
  if (!info) return <div className="container py-12">Loading...</div>;

  if (info.has_existing_account) {
    return (
      <div className="container max-w-md mx-auto py-12">
        <h1 className="text-2xl font-bold mb-4">チーム招待: {info.team_name}</h1>
        <p className="mb-4">この email には既にアカウントがあります。ログインしてから受諾してください。</p>
        <a href={`/login?next=${encodeURIComponent(`/accept-invitation?token=${token}&continue=accept`)}`}
           className="block p-2 bg-blue-600 text-white rounded text-center">
          ログイン
        </a>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-2">チーム招待: {info.team_name}</h1>
      <p className="mb-4">役割: {info.role}</p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input value={info.email} disabled className="w-full p-2 border rounded bg-gray-100" />
        <input
          required value={name} onChange={(e) => setName(e.target.value)}
          placeholder="お名前" className="w-full p-2 border rounded"
        />
        <input
          type="password" required minLength={8}
          value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="パスワード（8文字以上）" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "アカウント作成して参加"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: password-reset 画面 2 つ**

`app/src/app/password-reset/request/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth/client";


export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authClient.requestPasswordReset(email);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="container max-w-md mx-auto py-12">
        <h1 className="text-2xl font-bold mb-4">確認</h1>
        <p>該当する email が登録されている場合、リセット手順を記載したメールを送信しました。</p>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">パスワードリセット</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
        />
        <button type="submit" className="w-full p-2 bg-blue-600 text-white rounded">送信</button>
      </form>
    </div>
  );
}
```

`app/src/app/password-reset/confirm/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth/client";
import { AuthApiError } from "@/lib/auth/errors";


export default function PasswordResetConfirmPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      await authClient.confirmPasswordReset(token, password);
      router.push("/login?reset=success");
    } catch (err) {
      setError(err instanceof AuthApiError ? err.detail : "Failed");
    } finally {
      setLoading(false);
    }
  };

  if (!token) return <div className="container py-12"><p>無効なリンクです。</p></div>;

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">新しいパスワードを設定</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password" required minLength={8}
          value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="新しいパスワード（8文字以上）" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "更新"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: settings/profile, settings/password**

`app/src/app/settings/profile/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth/context";
import { apiFetch } from "@/lib/api";


export default function ProfileSettingsPage() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setMessage("");
    const res = await apiFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email }),
    });
    if (res.ok) setMessage("更新しました");
    else {
      const data = await res.json();
      setError(data.detail || "更新に失敗しました");
    }
  };

  if (!user) return null;

  return (
    <div className="container max-w-md py-8">
      <h1 className="text-2xl font-bold mb-6">プロフィール設定</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          value={name} onChange={(e) => setName(e.target.value)}
          placeholder="お名前" className="w-full p-2 border rounded"
        />
        <input
          type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
        />
        {message && <p className="text-green-600">{message}</p>}
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" className="w-full p-2 bg-blue-600 text-white rounded">更新</button>
      </form>
    </div>
  );
}
```

`app/src/app/settings/password/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { authClient } from "@/lib/auth/client";


export default function PasswordSettingsPage() {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    const res = await apiFetch("/api/auth/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    if (res.ok) {
      // 全 device からログアウトされるので /login へ
      await authClient.logout();
      router.push("/login?password_changed=1");
    } else {
      const data = await res.json();
      setError(data.detail || "更新に失敗しました");
    }
    setLoading(false);
  };

  return (
    <div className="container max-w-md py-8">
      <h1 className="text-2xl font-bold mb-6">パスワード変更</h1>
      <p className="text-sm text-gray-600 mb-4">
        パスワードを変更すると、全デバイスからログアウトされます。
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password" required
          value={current} onChange={(e) => setCurrent(e.target.value)}
          placeholder="現在のパスワード" className="w-full p-2 border rounded"
        />
        <input
          type="password" required minLength={8}
          value={next} onChange={(e) => setNext(e.target.value)}
          placeholder="新しいパスワード" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "変更"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: 動作確認**

```bash
cd app && npm run dev
```

ブラウザで各ページを開いて表示確認:
- http://localhost:3000/login
- http://localhost:3000/password-reset/request
- http://localhost:3000/settings/profile（要ログイン）

- [ ] **Step 6: コミット**

```bash
git add app/src/app/login app/src/app/accept-invitation app/src/app/password-reset app/src/app/settings
git commit -m "feat(ui): add login, invitation, password reset, settings pages without Supabase"
```

### Task 6.8: Supabase 撤去

**Files:**
- Delete: `app/src/lib/supabase/`（ディレクトリ丸ごと）
- Modify: `app/package.json`（@supabase/* 削除）
- Modify: `app/.env.example`（NEXT_PUBLIC_SUPABASE_* 削除）

- [ ] **Step 1: 残存 Supabase 利用箇所の確認**

```bash
cd app && grep -rn "@supabase\|supabase/ssr" src/ | grep -v ".next/" | head -20
```

期待: 何もヒットしないか、login/page.tsx 旧版の残骸のみ。あれば削除。

- [ ] **Step 2: ディレクトリ削除**

```bash
cd app && git rm -rf src/lib/supabase
```

- [ ] **Step 3: package.json から依存削除**

```bash
cd app && npm uninstall @supabase/ssr @supabase/supabase-js
```

- [ ] **Step 4: .env.example 更新**

`app/.env.example` を更新:

```bash
# 必須
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_SUPABASE_URL` と `NEXT_PUBLIC_SUPABASE_ANON_KEY` を削除。

- [ ] **Step 5: 動作確認**

```bash
cd app && npm run build
```

期待: ビルドエラーなし（Supabase import が残っていれば失敗 → 修正）。

- [ ] **Step 6: コミット**

```bash
git add app/
git commit -m "feat(ui): remove Supabase client dependency"
```

### Task 6.9: next.config.js dev rewrites（同一 origin 化）

**Files:**
- Modify: `app/next.config.js`

- [ ] **Step 1: 現状確認**

```bash
cat app/next.config.js
```

- [ ] **Step 2: rewrites 追加**

`app/next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 既存の設定 ...
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      return [
        { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
```

ローカル開発時は `NEXT_PUBLIC_API_URL` を空にして、相対パス `/api/*` で API を叩くと同一 origin として動く。

- [ ] **Step 3: 動作確認**

```bash
cd app && rm .env.local 2>/dev/null
npm run dev
```

別ターミナル:

```bash
curl http://localhost:3000/api/health
```

期待: API レスポンスが返る（rewrites 経由で localhost:8000 にプロキシ）。

- [ ] **Step 4: コミット**

```bash
git add app/next.config.js
git commit -m "feat(ui): add dev rewrites to proxy /api/* (same-origin in development)"
```

---

## Phase 7: ドキュメント更新

### Task 7.1: `docs/AUTH_SETUP.md` 作成

**Files:**
- Create: `docs/AUTH_SETUP.md`

- [ ] **Step 1: 作成**

`docs/AUTH_SETUP.md`:

```markdown
# 認証セットアップガイド

geo-base は 2 つの認証プロバイダをサポートします:

- **local**: geo-base 自身が users テーブルを所有し、JWT を発行（Supabase 不要）
- **supabase**: Supabase Auth に委譲（既存環境）

## クイックスタート（local モード）

### 1. 環境変数

`api/.env`:

\`\`\`bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base
AUTH_PROVIDER=local
JWT_SECRET=（openssl rand -base64 64 で生成）
EMAIL_BACKEND=console
INVITATION_BASE_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
\`\`\`

### 2. 初期管理者作成

\`\`\`bash
cd api
uv run python -m lib.auth.cli create-admin --email admin@example.com
# パスワードを対話入力
\`\`\`

### 3. API 起動

\`\`\`bash
uv run uvicorn lib.main:app --reload --port 8000
\`\`\`

### 4. Admin UI 起動

\`\`\`bash
cd app
npm install
npm run dev
\`\`\`

http://localhost:3000/login で admin@example.com にてログイン。

## 環境変数リファレンス

（スペック §9.1 参照）

## トラブルシューティング

- **JWT_SECRET 未設定**: `AUTH_PROVIDER=local` 時は必須。openssl rand で 64 バイト以上生成
- **CORS エラー**: `CORS_ORIGINS` に Admin UI の origin を含める
- **メールが届かない（local モード）**: `EMAIL_BACKEND=console` ならコンソールに出力される
- **ログインがロックされる**: 同一 IP/email から 5 回失敗で 15 分ロック
```

- [ ] **Step 2: コミット**

```bash
git add docs/AUTH_SETUP.md
git commit -m "docs: add AUTH_SETUP.md guide"
```

### Task 7.2: `docs/AUTH_MIGRATION.md` 作成

**Files:**
- Create: `docs/AUTH_MIGRATION.md`

- [ ] **Step 1: 作成**

`docs/AUTH_MIGRATION.md`:

```markdown
# Supabase Auth → local 移行手順

geo-base の認証バックエンドを Supabase から local に切り替える手順。

## 前提

- 本番ユーザーは greenfield（既存ユーザーなし or 開発者のみ）
- Postgres は引き続き Supabase を使用（または別 Postgres プロバイダ）

## 手順

### 1. コード配備（AUTH_PROVIDER=supabase のまま）

新しい auth 実装を含むコードをデプロイ。`AUTH_PROVIDER=supabase` のままなら現行と同じ挙動。

### 2. スキーマ追加

\`docker/postgis-init/04_auth_schema.sql\` の内容を本番 DB に適用:

\`\`\`bash
psql $DATABASE_URL -f docker/postgis-init/04_auth_schema.sql
\`\`\`

### 3. JWT_SECRET 設定

\`\`\`bash
cd api
fly secrets set JWT_SECRET=$(openssl rand -base64 64)
fly secrets set EMAIL_BACKEND=smtp \\
                SMTP_HOST=smtp.sendgrid.net \\
                SMTP_USER=apikey \\
                SMTP_PASSWORD=<sendgrid-api-key> \\
                SMTP_FROM=no-reply@geo-base.example
\`\`\`

### 4. 初期管理者作成

\`\`\`bash
fly ssh console -C "cd /app && uv run python -m lib.auth.cli create-admin --email <admin-email>"
\`\`\`

### 5. AUTH_PROVIDER 切り替え

\`\`\`bash
fly secrets set AUTH_PROVIDER=local COOKIE_SAMESITE=none COOKIE_SECURE=true
\`\`\`

API が再起動される。

### 6. 動作確認

- API ヘルスチェック: \`curl https://geo-base-api.fly.dev/api/health\`
- Admin UI ログイン: 新管理者でログイン

### ロールバック

問題が発生したら \`fly secrets set AUTH_PROVIDER=supabase\` で即座に戻せる。新規 users テーブルは残るが影響なし。

## 既存 Supabase ユーザーがいる場合

スペック §1.3 の通り、Phase 3 では移行スクリプトは提供しない。Phase 4 で対応予定。
```

- [ ] **Step 2: コミット**

```bash
git add docs/AUTH_MIGRATION.md
git commit -m "docs: add AUTH_MIGRATION.md (supabase → local cutover)"
```

### Task 7.3: 既存ドキュメント更新

**Files:**
- Modify: `LOCAL_DEVELOPMENT.md`
- Modify: `api/README.md`
- Modify: `app/README.md`
- Modify: `CLAUDE.md`
- Modify: `HANDOVER_S3.md`

- [ ] **Step 1: LOCAL_DEVELOPMENT.md 更新**

環境変数セクションに新規変数を追加、Supabase 関連を削除。`docs/AUTH_SETUP.md` への参照を追加。

- [ ] **Step 2: api/README.md 更新**

プロジェクト構造セクションに `lib/auth/` パッケージ、`lib/cors_middleware.py`、`routers/auth.py` を追加。API エンドポイント一覧に `/api/auth/*` を追加。

- [ ] **Step 3: app/README.md 更新**

「Supabase Auth 連携」セクションを削除、AuthClient の説明を追加。`/accept-invitation`, `/password-reset/*`, `/settings/profile|password` を機能一覧に追加。

- [ ] **Step 4: CLAUDE.md 更新**

「認証プロバイダ」セクションを追加:

```markdown
## 認証

- 環境変数 `AUTH_PROVIDER=local|supabase` で切替（Phase 3 / Step 3.3-A で実装）
- local モード: `users` テーブル + 自前 JWT 発行（`uv run python -m lib.auth.cli create-admin` で初期管理者作成）
- supabase モード: 従来通り Supabase Auth に委譲
- 詳細: `docs/AUTH_SETUP.md`、設計: `docs/specs/2026-05-08-pluggable-auth-design.md`
```

- [ ] **Step 5: HANDOVER_S3.md 更新**

Step 3.3-A の進捗を「設計完了 → 実装中 / 完了」に更新。

- [ ] **Step 6: コミット**

```bash
git add LOCAL_DEVELOPMENT.md api/README.md app/README.md CLAUDE.md HANDOVER_S3.md
git commit -m "docs: update existing docs for pluggable auth implementation"
```

---

## Phase 8: 統合検証

### Task 8.1: 全テスト実行

- [ ] **Step 1: フルテストスイート実行**

```bash
cd api && uv run pytest tests/ -v --tb=short 2>&1 | tee /tmp/test-results.txt | tail -30
```

期待: 全テスト PASS、カバレッジ ≥ 85%。

- [ ] **Step 2: カバレッジレポート**

```bash
cd api && uv run pytest tests/ --cov=lib --cov-report=term-missing 2>&1 | tail -50
```

カバレッジ目標を満たさない部分があればテスト追加。

- [ ] **Step 3: コミット（テスト追加があれば）**

### Task 8.2: ローカル E2E（local モード）

- [ ] **Step 1: クリーン起動**

```bash
cd docker && docker compose down -v && docker compose up -d
sleep 10

cd ../api
cat > .env <<EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base
AUTH_PROVIDER=local
JWT_SECRET=$(openssl rand -base64 64)
EMAIL_BACKEND=console
INVITATION_BASE_URL=http://localhost:3000
CORS_ORIGINS=["http://localhost:3000"]
EOF

uv run python -m lib.auth.cli create-admin --email admin@local.test
# パスワード TestPass123 を入力
```

- [ ] **Step 2: API + UI 起動**

```bash
# Terminal 1
cd api && uv run uvicorn lib.main:app --reload --port 8000

# Terminal 2
cd app && npm run dev
```

- [ ] **Step 3: 手動 E2E チェックリスト**

ブラウザ http://localhost:3000 で以下を確認:

- [ ] /login で admin@local.test / TestPass123 でログイン成功
- [ ] /tilesets が表示される
- [ ] /settings/profile で名前を変更できる
- [ ] /settings/password でパスワード変更できる（変更後ログアウトされる）
- [ ] チーム作成 → 招待発行 → ターミナルにメール内容（招待リンク）が表示される
- [ ] 招待リンクをコピーして別ブラウザで開く → /accept-invitation 画面
- [ ] サインアップ → 自動ログイン → チーム参加完了
- [ ] /password-reset/request → コンソールにリセットメール表示
- [ ] リセットリンク経由で新パスワード設定 → 旧パスワードで失敗、新で成功

### Task 8.3: ローカル E2E（supabase モード）

- [ ] **Step 1: 設定切替**

`api/.env` を Supabase モード用に変更:

```bash
AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-test-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<test-service-role-key>
SUPABASE_JWT_SECRET=<test-jwt-secret>
```

- [ ] **Step 2: 起動 + E2E**

API 再起動 → Admin UI で Supabase に登録済みのテストユーザーでログイン。基本動作（タイル一覧、チーム表示等）を確認。

### Task 8.4: 最終コミットとサマリ

- [ ] **Step 1: HANDOVER_S3.md に Phase 3 完了記録**

`HANDOVER_S3.md` の進捗テーブルで Step 3.3-A を完了マークに更新、テスト件数と実装規模を追記。

- [ ] **Step 2: docs/INFRA_MIGRATION_INVESTIGATION.md の「Phase 3 で実施した準備工程」セクションを実績で更新**

```markdown
## Phase 3 で実施済みの準備工程（2026-05-XX 完了）

- ✅ `api/lib/auth.py` をパッケージ化、JWT 発行者非依存にリファクタ
- ✅ 新規 RLS は permissive のまま、アプリ層認可で対応（Phase 4 でポータブル RLS 化予定）
- ✅ Admin UI の Supabase クライアントを完全撤去（`app/src/lib/auth/` で抽象化）
- ✅ Supabase 固有 Postgres 拡張は使っていないことを確認

将来 Cloudflare 寄せ移行する際、認証層の手直しは不要となる状態を確立。
```

- [ ] **Step 3: 最終コミット**

```bash
git add HANDOVER_S3.md docs/INFRA_MIGRATION_INVESTIGATION.md
git commit -m "docs: mark Phase 3 / Step 3.3-A complete with implementation summary"
```

- [ ] **Step 4: ブランチ整理確認**

```bash
git log --oneline -30
git status
```

期待: クリーンな履歴、未コミット変更なし。

---

## 実装完了基準

以下が全て満たされたら Phase 3 / Step 3.3-A 完了:

- [ ] 全 350+ テストが PASS
- [ ] カバレッジ ≥ 85%
- [ ] local モード E2E 全項目クリア
- [ ] supabase モード E2E 全項目クリア
- [ ] CORS: `/api/auth/*` strict、それ以外 `*`
- [ ] Cookie: HttpOnly + 適切な SameSite/Secure
- [ ] CLI コマンドが全て動作
- [ ] 設定検証が起動時に fail-fast
- [ ] Admin UI に Supabase クライアントが残っていない（`grep -rn "@supabase" app/src` が空）
- [ ] `docs/AUTH_SETUP.md`, `docs/AUTH_MIGRATION.md` 完備
- [ ] CLAUDE.md / HANDOVER_S3.md に最新情報反映

---

## 補足: Phase 4 以降への引き継ぎ

実装中に発見した課題・将来対応すべき事項は以下に記録:

- パスワードリセットメール内のトークン抽出（テスト用ヘルパー）→ E2E テストフレームワークと統合
- `pg_cron` を使わないので、`cleanup-expired` を呼ぶ仕組みが必要（Fly.io scheduled machines or 外部 cron）
- `lib.auth.cli` の対話的入力テストはサブプロセス + stdin で書く（Phase 3 では smoke のみ）
- `SupabaseAuthProvider` の confirm_password_reset は Supabase の OTP verify 仕様に依存。実環境で動作確認が必要
- API キー使用ログのサンプリング: 本番で `API_KEY_LOG_SAMPLE_RATE=0.1` 程度を推奨
- フロントエンドの E2E テスト（Playwright 等）は Phase 4
- ポータブル RLS（`current_setting('app.user_id')`）への移行は Phase 4
