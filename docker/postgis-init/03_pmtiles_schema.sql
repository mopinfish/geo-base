-- ============================================================================
-- PMTiles Sources Schema
-- ============================================================================
-- This file creates the pmtiles_sources table for storing PMTiles metadata
-- Run after 01_init.sql

-- PMTiles source table
-- Stores references to PMTiles files hosted on external storage (Fly Tigris / S3 / HTTP).
CREATE TABLE IF NOT EXISTS pmtiles_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL REFERENCES tilesets(id) ON DELETE CASCADE,

    -- PMTiles file location
    pmtiles_url TEXT NOT NULL,              -- URL to the PMTiles file
    -- 's3' は AWS S3 / Fly Tigris / R2 / MinIO 等 S3 互換 storage の総称。
    -- Supabase Storage は Issue #72 (PR #88) で廃止済み。
    storage_provider VARCHAR(50) DEFAULT 's3',  -- 's3' or 'http'
    
    -- Metadata from PMTiles header (cached for performance)
    tile_type VARCHAR(20),                  -- 'vector', 'raster', 'unknown'
    tile_compression VARCHAR(20),           -- 'gzip', 'zstd', 'br', 'none'
    min_zoom INTEGER,
    max_zoom INTEGER,
    bounds JSONB,                           -- [west, south, east, north]
    center JSONB,                           -- [lng, lat, zoom]
    
    -- Additional metadata
    layers JSONB DEFAULT '[]',              -- Vector layer info for MVT
    metadata JSONB DEFAULT '{}',            -- Original PMTiles metadata
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one PMTiles source per tileset
    UNIQUE (tileset_id)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_pmtiles_sources_tileset_id ON pmtiles_sources(tileset_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_pmtiles_sources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_pmtiles_sources_updated_at ON pmtiles_sources;
CREATE TRIGGER trigger_pmtiles_sources_updated_at
    BEFORE UPDATE ON pmtiles_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_pmtiles_sources_updated_at();

-- Comments
COMMENT ON TABLE pmtiles_sources IS 'Stores references to PMTiles files for tile serving';
COMMENT ON COLUMN pmtiles_sources.pmtiles_url IS 'URL to the PMTiles file (supports HTTP range requests)';
COMMENT ON COLUMN pmtiles_sources.storage_provider IS 'Storage provider: s3 (S3 互換: Fly Tigris / AWS S3 / R2 等) or http';
COMMENT ON COLUMN pmtiles_sources.tile_type IS 'Type of tiles: vector or raster';
COMMENT ON COLUMN pmtiles_sources.tile_compression IS 'Compression used: gzip, zstd, br, or none';
