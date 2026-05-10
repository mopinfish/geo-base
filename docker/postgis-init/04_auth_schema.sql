-- =============================================================================
-- geo-base Authentication Schema (Phase 3 / Step 3.3-A)
-- =============================================================================
-- 認証関連テーブル（AUTH_PROVIDER=local が唯一サポートされるモード）。
-- 旧 supabase モードでは auth.users が代替していたが、Issue #72 で完全廃止済み。
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

COMMENT ON TABLE users IS 'ユーザーアカウント（AUTH_PROVIDER=local の自前認証で使用）';

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
