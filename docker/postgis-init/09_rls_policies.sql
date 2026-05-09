-- ============================================================================
-- Row Level Security (RLS) - Local Development Version
-- ============================================================================
-- RLS is disabled for local development.
-- The API handles authorization in the application layer.
-- For production (Supabase), use 04_rls_policies.sql.supabase

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
