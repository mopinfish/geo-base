-- ============================================================================
-- Row Level Security (RLS) Policies for Supabase
-- ============================================================================
-- This file sets up RLS policies for access control
-- Run in Supabase SQL Editor after enabling RLS

-- ============================================================================
-- Enable RLS on tables
-- ============================================================================

ALTER TABLE tilesets ENABLE ROW LEVEL SECURITY;
ALTER TABLE features ENABLE ROW LEVEL SECURITY;
ALTER TABLE pmtiles_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE raster_sources ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- Tilesets Policies
-- ============================================================================

-- Policy: Anyone can read public tilesets
CREATE POLICY "Public tilesets are viewable by everyone"
ON tilesets FOR SELECT
USING (is_public = true);

-- Policy: Authenticated users can read their own private tilesets
CREATE POLICY "Users can view own tilesets"
ON tilesets FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy: Authenticated users can insert their own tilesets
CREATE POLICY "Users can create tilesets"
ON tilesets FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy: Authenticated users can update their own tilesets
CREATE POLICY "Users can update own tilesets"
ON tilesets FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy: Authenticated users can delete their own tilesets
CREATE POLICY "Users can delete own tilesets"
ON tilesets FOR DELETE
TO authenticated
USING (auth.uid() = user_id);


-- ============================================================================
-- Features Policies
-- ============================================================================

-- Policy: Anyone can read features from public tilesets
CREATE POLICY "Features from public tilesets are viewable by everyone"
ON features FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.is_public = true
    )
);

-- Policy: Authenticated users can read features from their own tilesets
CREATE POLICY "Users can view features from own tilesets"
ON features FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);

-- Policy: Authenticated users can insert features to their own tilesets
CREATE POLICY "Users can create features in own tilesets"
ON features FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);

-- Policy: Authenticated users can update features in their own tilesets
CREATE POLICY "Users can update features in own tilesets"
ON features FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.user_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);

-- Policy: Authenticated users can delete features from their own tilesets
CREATE POLICY "Users can delete features from own tilesets"
ON features FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = features.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);


-- ============================================================================
-- PMTiles Sources Policies
-- ============================================================================

-- Policy: Anyone can read PMTiles sources from public tilesets
CREATE POLICY "PMTiles sources from public tilesets are viewable by everyone"
ON pmtiles_sources FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = pmtiles_sources.tileset_id
        AND tilesets.is_public = true
    )
);

-- Policy: Authenticated users can read PMTiles sources from their own tilesets
CREATE POLICY "Users can view PMTiles sources from own tilesets"
ON pmtiles_sources FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = pmtiles_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);

-- Policy: Authenticated users can manage PMTiles sources in their own tilesets
CREATE POLICY "Users can manage PMTiles sources in own tilesets"
ON pmtiles_sources FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = pmtiles_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = pmtiles_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);


-- ============================================================================
-- Raster Sources Policies
-- ============================================================================

-- Policy: Anyone can read raster sources from public tilesets
CREATE POLICY "Raster sources from public tilesets are viewable by everyone"
ON raster_sources FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = raster_sources.tileset_id
        AND tilesets.is_public = true
    )
);

-- Policy: Authenticated users can read raster sources from their own tilesets
CREATE POLICY "Users can view raster sources from own tilesets"
ON raster_sources FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = raster_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);

-- Policy: Authenticated users can manage raster sources in their own tilesets
CREATE POLICY "Users can manage raster sources in own tilesets"
ON raster_sources FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = raster_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM tilesets
        WHERE tilesets.id = raster_sources.tileset_id
        AND tilesets.user_id = auth.uid()
    )
);


-- ============================================================================
-- Service Role Bypass (for API)
-- ============================================================================
-- Note: The API uses SUPABASE_SERVICE_ROLE_KEY which bypasses RLS
-- This is intentional as the API handles authorization in the application layer
-- For direct database access via Supabase client, RLS will be enforced


-- ============================================================================
-- Helper function to check tileset ownership
-- ============================================================================

CREATE OR REPLACE FUNCTION is_tileset_owner(tileset_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM tilesets
        WHERE id = tileset_uuid
        AND user_id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON POLICY "Public tilesets are viewable by everyone" ON tilesets IS 
'Allow anonymous access to public tilesets';

COMMENT ON POLICY "Users can view own tilesets" ON tilesets IS 
'Allow authenticated users to view their own private tilesets';

COMMENT ON FUNCTION is_tileset_owner IS
'Helper function to check if current user owns a tileset';
