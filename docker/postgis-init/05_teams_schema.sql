-- =============================================================================
-- geo-base Team Management Schema
-- =============================================================================
-- This file defines the database schema for team management functionality.
-- Run after 01_init.sql, 02_raster_schema.sql, 03_pmtiles_schema.sql
--
-- Features:
-- - Teams table with ownership
-- - Team members with role-based access control
-- - Team invitations with expiration
-- - Tileset-team associations for shared access
-- =============================================================================

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

-- Team member roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'team_role') THEN
        CREATE TYPE team_role AS ENUM ('owner', 'administrator', 'member', 'guest');
    END IF;
END$$;

-- Invitation status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitation_status') THEN
        CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'declined', 'expired', 'cancelled');
    END IF;
END$$;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE teams IS 'チーム/組織の管理テーブル';
COMMENT ON COLUMN teams.slug IS 'URLフレンドリーな一意識別子';
COMMENT ON COLUMN teams.owner_id IS 'チームのオーナー（Supabase auth.usersのID）';

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role team_role NOT NULL DEFAULT 'member',
    notification_enabled BOOLEAN DEFAULT true,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

COMMENT ON TABLE team_members IS 'チームメンバーシップの管理テーブル';

-- Team invitations table
CREATE TABLE IF NOT EXISTS team_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role team_role NOT NULL DEFAULT 'member',
    invited_by UUID NOT NULL,
    message TEXT,
    token VARCHAR(64) UNIQUE NOT NULL,
    status invitation_status NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_pending_invitation UNIQUE (team_id, email, status)
);

COMMENT ON TABLE team_invitations IS 'チーム招待の管理テーブル';

-- Tileset-Team association table
CREATE TABLE IF NOT EXISTS team_tilesets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    tileset_id UUID NOT NULL REFERENCES tilesets(id) ON DELETE CASCADE,
    added_by UUID NOT NULL,
    permission_level VARCHAR(20) CHECK (permission_level IN ('read', 'write', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, tileset_id)
);

COMMENT ON TABLE team_tilesets IS 'チームとタイルセットの関連付けテーブル';

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_teams_owner_id ON teams (owner_id);
CREATE INDEX IF NOT EXISTS idx_teams_slug ON teams (slug);
CREATE INDEX IF NOT EXISTS idx_teams_created_at ON teams (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members (team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members (user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_role ON team_members (role);

CREATE INDEX IF NOT EXISTS idx_team_invitations_team_id ON team_invitations (team_id);
CREATE INDEX IF NOT EXISTS idx_team_invitations_email ON team_invitations (email);
CREATE INDEX IF NOT EXISTS idx_team_invitations_token ON team_invitations (token);
CREATE INDEX IF NOT EXISTS idx_team_invitations_status ON team_invitations (status);
CREATE INDEX IF NOT EXISTS idx_team_invitations_expires_at ON team_invitations (expires_at);

CREATE INDEX IF NOT EXISTS idx_team_tilesets_team_id ON team_tilesets (team_id);
CREATE INDEX IF NOT EXISTS idx_team_tilesets_tileset_id ON team_tilesets (tileset_id);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_team_members_updated_at ON team_members;
CREATE TRIGGER update_team_members_updated_at
    BEFORE UPDATE ON team_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION generate_invitation_token()
RETURNS VARCHAR(64) AS $$
DECLARE
    chars TEXT := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    result VARCHAR(64) := '';
    i INTEGER;
BEGIN
    FOR i IN 1..64 LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::INTEGER, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_team_permission(
    p_user_id UUID,
    p_tileset_id UUID
) RETURNS VARCHAR(20) AS $$
DECLARE
    v_permission VARCHAR(20);
BEGIN
    IF EXISTS (SELECT 1 FROM tilesets WHERE id = p_tileset_id AND user_id = p_user_id) THEN
        RETURN 'admin';
    END IF;

    SELECT COALESCE(tt.permission_level, 
        CASE tm.role
            WHEN 'owner' THEN 'admin'
            WHEN 'administrator' THEN 'admin'
            WHEN 'member' THEN 'write'
            WHEN 'guest' THEN 'read'
            ELSE 'read'
        END)
    INTO v_permission
    FROM team_members tm
    JOIN team_tilesets tt ON tm.team_id = tt.team_id
    WHERE tm.user_id = p_user_id AND tt.tileset_id = p_tileset_id
    ORDER BY 
        CASE COALESCE(tt.permission_level, 
            CASE tm.role
                WHEN 'owner' THEN 'admin'
                WHEN 'administrator' THEN 'admin'
                WHEN 'member' THEN 'write'
                WHEN 'guest' THEN 'read'
            END)
            WHEN 'admin' THEN 1
            WHEN 'write' THEN 2
            WHEN 'read' THEN 3
        END
    LIMIT 1;

    RETURN v_permission;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION can_user_perform_action(
    p_user_id UUID,
    p_tileset_id UUID,
    p_action VARCHAR(20)
) RETURNS BOOLEAN AS $$
DECLARE
    v_permission VARCHAR(20);
BEGIN
    v_permission := get_team_permission(p_user_id, p_tileset_id);
    
    IF v_permission IS NULL THEN
        RETURN FALSE;
    END IF;

    CASE p_action
        WHEN 'read' THEN RETURN v_permission IN ('read', 'write', 'admin');
        WHEN 'create' THEN RETURN v_permission IN ('write', 'admin');
        WHEN 'update' THEN RETURN v_permission IN ('write', 'admin');
        WHEN 'delete' THEN RETURN v_permission = 'admin';
        ELSE RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auto_add_team_owner()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO team_members (team_id, user_id, role)
    VALUES (NEW.id, NEW.owner_id, 'owner')
    ON CONFLICT (team_id, user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_auto_add_team_owner ON teams;
CREATE TRIGGER trigger_auto_add_team_owner
    AFTER INSERT ON teams
    FOR EACH ROW
    EXECUTE FUNCTION auto_add_team_owner();

CREATE OR REPLACE FUNCTION expire_old_invitations()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE team_invitations SET status = 'expired'
    WHERE status = 'pending' AND expires_at < NOW();
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS
-- =============================================================================

CREATE OR REPLACE VIEW v_team_details AS
SELECT 
    t.id, t.name, t.slug, t.description, t.owner_id, t.settings,
    t.created_at, t.updated_at,
    COUNT(DISTINCT tm.user_id) AS member_count,
    COUNT(DISTINCT tt.tileset_id) AS tileset_count
FROM teams t
LEFT JOIN team_members tm ON t.id = tm.team_id
LEFT JOIN team_tilesets tt ON t.id = tt.team_id
GROUP BY t.id, t.name, t.slug, t.description, t.owner_id, t.settings, t.created_at, t.updated_at;

CREATE OR REPLACE VIEW v_user_teams AS
SELECT 
    tm.user_id, t.id AS team_id, t.name AS team_name, t.slug AS team_slug,
    t.description AS team_description, t.owner_id, tm.role, tm.joined_at,
    (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) AS member_count
FROM team_members tm
JOIN teams t ON tm.team_id = t.id;

-- Permission Matrix:
-- +---------------+---------+--------+--------+--------+
-- | Resource      | owner   | admin  | member | guest  |
-- +---------------+---------+--------+--------+--------+
-- | Tileset Read  |   ✓     |   ✓    |   ✓    |   ✓    |
-- | Tileset Create|   ✓     |   ✓    |   ✓    |   ✗    |
-- | Tileset Update|   ✓     |   ✓    |   ✓    |   ✗    |
-- | Tileset Delete|   ✓     |   ✓    |   ✗    |   ✗    |
-- +---------------+---------+--------+--------+--------+
-- | Team Manage   |   ✓     |   ✓*   |   ✗    |   ✗    |
-- | Team Delete   |   ✓     |   ✗    |   ✗    |   ✗    |
-- +---------------+---------+--------+--------+--------+
-- * admin can manage members but not delete team or remove owner
