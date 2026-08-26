-- ============================================================================
-- Row Level Security (RLS) - Local Development Version
-- ============================================================================
-- API がアプリ層で認可を行うため、RLS は permissive のまま。本番 (Fly Postgres,
-- geo-base-pg) では `pg/Dockerfile` でこのファイルを焼き込まないことで
-- "RLS 無効 + アプリ層 authz のみ" にしている。詳細は Issue #72 Phase 1.5 と
-- docs/POSTGRES_SETUP.md 参照。
--
-- 旧 Supabase 用 RLS バリアント (`09_rls_policies.sql.supabase`) は Issue #72 で削除済み。

-- Enable RLS but with permissive policies for local development
ALTER TABLE tilesets ENABLE ROW LEVEL SECURITY;
ALTER TABLE features ENABLE ROW LEVEL SECURITY;
ALTER TABLE pmtiles_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE raster_sources ENABLE ROW LEVEL SECURITY;

-- Allow all operations for local development
CREATE POLICY "Allow all tilesets for local dev" ON tilesets FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all features for local dev" ON features FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all pmtiles for local dev" ON pmtiles_sources FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all raster for local dev" ON raster_sources FOR ALL USING (true) WITH CHECK (true);

-- Comments
COMMENT ON POLICY "Allow all tilesets for local dev" ON tilesets IS 'Permissive policy for local development';
