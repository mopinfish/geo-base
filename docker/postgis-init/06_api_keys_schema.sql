-- =============================================================================
-- geo-base API Keys Schema
-- =============================================================================
-- This file defines the database schema for API key management.
-- Run after 05_teams_schema.sql
--
-- Features:
-- - API keys with secure hash storage
-- - Team-scoped keys (optional)
-- - Rate limiting configuration
-- - Usage tracking
-- - Key scopes for fine-grained permissions
-- =============================================================================

-- =============================================================================
-- TABLES
-- =============================================================================

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Key identification
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prefix VARCHAR(12) NOT NULL,  -- First 12 chars for identification (e.g., "gb_live_abc1")
    key_hash VARCHAR(128) NOT NULL,  -- SHA-256 hash of the full key
    
    -- Ownership
    user_id UUID NOT NULL,  -- Key creator/owner
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,  -- Optional team association
    
    -- Permissions
    scopes TEXT[] DEFAULT ARRAY['read']::TEXT[],  -- ['read', 'write', 'delete', 'admin']
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 10000,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID,
    revoke_reason TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_key_hash UNIQUE (key_hash),
    CONSTRAINT unique_prefix UNIQUE (prefix)
);

COMMENT ON TABLE api_keys IS 'APIキーの管理テーブル';
COMMENT ON COLUMN api_keys.prefix IS 'キーの識別用プレフィックス（表示用）';
COMMENT ON COLUMN api_keys.key_hash IS 'キーのSHA-256ハッシュ（検証用）';
COMMENT ON COLUMN api_keys.scopes IS '許可されたスコープ: read, write, delete, admin';

-- API Key Usage Logs table
CREATE TABLE IF NOT EXISTS api_key_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    
    -- Request info
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    
    -- Client info
    ip_address INET,
    user_agent TEXT,
    
    -- Rate limit info
    rate_limit_remaining INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE api_key_usage_logs IS 'APIキー使用ログ';

-- Rate Limit Counters table (for Redis fallback or persistence)
CREATE TABLE IF NOT EXISTS api_key_rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    window_type VARCHAR(20) NOT NULL,  -- 'minute' or 'day'
    window_start TIMESTAMPTZ NOT NULL,
    request_count INTEGER DEFAULT 0,
    
    CONSTRAINT unique_rate_limit_window UNIQUE (api_key_id, window_type, window_start)
);

COMMENT ON TABLE api_key_rate_limits IS 'APIキーのレート制限カウンター';

-- =============================================================================
-- INDEXES
-- =============================================================================

-- API Keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_team_id ON api_keys (team_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys (prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys (created_at DESC);

-- Usage logs indexes
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_api_key_id ON api_key_usage_logs (api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_created_at ON api_key_usage_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_logs_api_key_created ON api_key_usage_logs (api_key_id, created_at DESC);

-- Rate limits indexes
CREATE INDEX IF NOT EXISTS idx_api_key_rate_limits_lookup ON api_key_rate_limits (api_key_id, window_type, window_start);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Update timestamp trigger
DROP TRIGGER IF EXISTS update_api_keys_updated_at ON api_keys;
CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Validate API key and return key info
CREATE OR REPLACE FUNCTION validate_api_key(p_key_hash VARCHAR(128))
RETURNS TABLE (
    key_id UUID,
    user_id UUID,
    team_id UUID,
    scopes TEXT[],
    rate_limit_per_minute INTEGER,
    rate_limit_per_day INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ak.id,
        ak.user_id,
        ak.team_id,
        ak.scopes,
        ak.rate_limit_per_minute,
        ak.rate_limit_per_day
    FROM api_keys ak
    WHERE ak.key_hash = p_key_hash
      AND ak.is_active = true
      AND ak.revoked_at IS NULL
      AND (ak.expires_at IS NULL OR ak.expires_at > NOW());
END;
$$ LANGUAGE plpgsql;

-- Check if key has required scope
CREATE OR REPLACE FUNCTION api_key_has_scope(p_key_id UUID, p_required_scope TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_scopes TEXT[];
BEGIN
    SELECT scopes INTO v_scopes FROM api_keys WHERE id = p_key_id;
    
    IF v_scopes IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- 'admin' scope grants all permissions
    IF 'admin' = ANY(v_scopes) THEN
        RETURN TRUE;
    END IF;
    
    -- 'write' scope includes 'read'
    IF p_required_scope = 'read' AND 'write' = ANY(v_scopes) THEN
        RETURN TRUE;
    END IF;
    
    -- 'delete' scope includes 'write' and 'read'
    IF p_required_scope IN ('read', 'write') AND 'delete' = ANY(v_scopes) THEN
        RETURN TRUE;
    END IF;
    
    RETURN p_required_scope = ANY(v_scopes);
END;
$$ LANGUAGE plpgsql;

-- Update last used timestamp
CREATE OR REPLACE FUNCTION update_api_key_last_used(p_key_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE api_keys SET last_used_at = NOW() WHERE id = p_key_id;
END;
$$ LANGUAGE plpgsql;

-- Get rate limit status for a key
CREATE OR REPLACE FUNCTION get_api_key_rate_limit_status(
    p_key_id UUID,
    p_window_type VARCHAR(20)
)
RETURNS TABLE (
    request_count INTEGER,
    rate_limit INTEGER,
    window_start TIMESTAMPTZ,
    remaining INTEGER
) AS $$
DECLARE
    v_window_start TIMESTAMPTZ;
    v_rate_limit INTEGER;
    v_count INTEGER;
BEGIN
    -- Calculate window start
    IF p_window_type = 'minute' THEN
        v_window_start := date_trunc('minute', NOW());
        SELECT rate_limit_per_minute INTO v_rate_limit FROM api_keys WHERE id = p_key_id;
    ELSE
        v_window_start := date_trunc('day', NOW());
        SELECT rate_limit_per_day INTO v_rate_limit FROM api_keys WHERE id = p_key_id;
    END IF;
    
    -- Get current count
    SELECT COALESCE(rl.request_count, 0) INTO v_count
    FROM api_key_rate_limits rl
    WHERE rl.api_key_id = p_key_id 
      AND rl.window_type = p_window_type 
      AND rl.window_start = v_window_start;
    
    IF v_count IS NULL THEN
        v_count := 0;
    END IF;
    
    RETURN QUERY SELECT v_count, v_rate_limit, v_window_start, GREATEST(0, v_rate_limit - v_count);
END;
$$ LANGUAGE plpgsql;

-- Increment rate limit counter
CREATE OR REPLACE FUNCTION increment_api_key_rate_limit(
    p_key_id UUID,
    p_window_type VARCHAR(20)
)
RETURNS INTEGER AS $$
DECLARE
    v_window_start TIMESTAMPTZ;
    v_new_count INTEGER;
BEGIN
    -- Calculate window start
    IF p_window_type = 'minute' THEN
        v_window_start := date_trunc('minute', NOW());
    ELSE
        v_window_start := date_trunc('day', NOW());
    END IF;
    
    -- Upsert counter
    INSERT INTO api_key_rate_limits (api_key_id, window_type, window_start, request_count)
    VALUES (p_key_id, p_window_type, v_window_start, 1)
    ON CONFLICT (api_key_id, window_type, window_start)
    DO UPDATE SET request_count = api_key_rate_limits.request_count + 1
    RETURNING request_count INTO v_new_count;
    
    RETURN v_new_count;
END;
$$ LANGUAGE plpgsql;

-- Clean up old rate limit records
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM api_key_rate_limits
    WHERE (window_type = 'minute' AND window_start < NOW() - INTERVAL '1 hour')
       OR (window_type = 'day' AND window_start < NOW() - INTERVAL '7 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Log API key usage
CREATE OR REPLACE FUNCTION log_api_key_usage(
    p_key_id UUID,
    p_endpoint VARCHAR(255),
    p_method VARCHAR(10),
    p_status_code INTEGER,
    p_response_time_ms INTEGER,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO api_key_usage_logs (
        api_key_id, endpoint, method, status_code, 
        response_time_ms, ip_address, user_agent
    )
    VALUES (
        p_key_id, p_endpoint, p_method, p_status_code,
        p_response_time_ms, p_ip_address, p_user_agent
    )
    RETURNING id INTO v_log_id;
    
    -- Also update last_used_at
    PERFORM update_api_key_last_used(p_key_id);
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Get API key usage statistics
CREATE OR REPLACE FUNCTION get_api_key_usage_stats(
    p_key_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_requests BIGINT,
    avg_response_time_ms NUMERIC,
    error_count BIGINT,
    success_rate NUMERIC,
    requests_by_day JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH daily_stats AS (
        SELECT 
            date_trunc('day', created_at)::DATE as day,
            COUNT(*) as count,
            AVG(response_time_ms) as avg_time,
            COUNT(*) FILTER (WHERE status_code >= 400) as errors
        FROM api_key_usage_logs
        WHERE api_key_id = p_key_id
          AND created_at >= NOW() - (p_days || ' days')::INTERVAL
        GROUP BY date_trunc('day', created_at)::DATE
    )
    SELECT 
        COALESCE(SUM(ds.count), 0)::BIGINT,
        COALESCE(AVG(ds.avg_time), 0)::NUMERIC,
        COALESCE(SUM(ds.errors), 0)::BIGINT,
        CASE 
            WHEN SUM(ds.count) > 0 
            THEN ((SUM(ds.count) - SUM(ds.errors))::NUMERIC / SUM(ds.count) * 100)
            ELSE 100
        END,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'date', ds.day,
                    'requests', ds.count,
                    'errors', ds.errors,
                    'avg_response_time', ROUND(ds.avg_time::NUMERIC, 2)
                ) ORDER BY ds.day
            ),
            '[]'::JSONB
        )
    FROM daily_stats ds;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Active API keys with usage stats
CREATE OR REPLACE VIEW v_api_keys_with_stats AS
SELECT 
    ak.id,
    ak.name,
    ak.description,
    ak.prefix,
    ak.user_id,
    ak.team_id,
    ak.scopes,
    ak.rate_limit_per_minute,
    ak.rate_limit_per_day,
    ak.is_active,
    ak.last_used_at,
    ak.expires_at,
    ak.created_at,
    ak.updated_at,
    t.name as team_name,
    COALESCE(usage.total_requests, 0) as total_requests_30d,
    COALESCE(usage.last_request_at, ak.last_used_at) as last_request_at
FROM api_keys ak
LEFT JOIN teams t ON ak.team_id = t.id
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) as total_requests,
        MAX(created_at) as last_request_at
    FROM api_key_usage_logs
    WHERE api_key_id = ak.id
      AND created_at >= NOW() - INTERVAL '30 days'
) usage ON true;

-- =============================================================================
-- COMMENTS
-- =============================================================================

-- Permission Scopes:
-- +--------+----------------------------------+
-- | Scope  | Permissions                      |
-- +--------+----------------------------------+
-- | read   | GET requests only               |
-- | write  | read + POST/PUT/PATCH requests  |
-- | delete | write + DELETE requests         |
-- | admin  | All permissions                 |
-- +--------+----------------------------------+

-- API Key Format:
-- gb_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
-- │  │    └── 32 random characters
-- │  └────── Environment (live/test)
-- └───────── Prefix (geo-base)
