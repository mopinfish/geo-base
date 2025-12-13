-- PostGIS拡張を有効化
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- UUID生成用
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- tilesetsテーブル
CREATE TABLE IF NOT EXISTS tilesets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('raster', 'vector', 'pmtiles')),
    format VARCHAR(50) NOT NULL CHECK (format IN ('png', 'jpg', 'webp', 'pbf', 'geojson', 'mbtiles', 'pmtiles', 'cog')),
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 22,
    bounds GEOMETRY(POLYGON, 4326),
    center GEOMETRY(POINT, 4326),
    attribution TEXT,
    is_public BOOLEAN DEFAULT false,
    user_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- featuresテーブル
CREATE TABLE IF NOT EXISTS features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID REFERENCES tilesets(id) ON DELETE CASCADE,
    layer_name VARCHAR(255) DEFAULT 'default',
    geom GEOMETRY NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- tile_filesテーブル（静的タイルファイル管理）
CREATE TABLE IF NOT EXISTS tile_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID REFERENCES tilesets(id) ON DELETE CASCADE,
    z INTEGER NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    blob_url TEXT NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tileset_id, z, x, y)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_tilesets_user_id ON tilesets (user_id);
CREATE INDEX IF NOT EXISTS idx_tilesets_is_public ON tilesets (is_public);
CREATE INDEX IF NOT EXISTS idx_tilesets_type ON tilesets (type);

CREATE INDEX IF NOT EXISTS idx_features_geom ON features USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_features_tileset_id ON features (tileset_id);
CREATE INDEX IF NOT EXISTS idx_features_layer_name ON features (layer_name);

CREATE INDEX IF NOT EXISTS idx_tile_files_coords ON tile_files (tileset_id, z, x, y);

-- updated_at自動更新用トリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガー適用
DROP TRIGGER IF EXISTS update_tilesets_updated_at ON tilesets;
CREATE TRIGGER update_tilesets_updated_at
    BEFORE UPDATE ON tilesets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_features_updated_at ON features;
CREATE TRIGGER update_features_updated_at
    BEFORE UPDATE ON features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- サンプルデータ（オプション）
-- INSERT INTO tilesets (name, description, type, format, is_public)
-- VALUES ('Sample Vector', 'Sample vector tileset', 'vector', 'pbf', true);

COMMENT ON TABLE tilesets IS 'タイルセットのメタデータを管理';
COMMENT ON TABLE features IS 'ベクタフィーチャーデータを格納';
COMMENT ON TABLE tile_files IS '静的タイルファイルの参照情報を管理';
