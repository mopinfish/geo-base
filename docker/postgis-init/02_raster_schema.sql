-- ============================================================================
-- ラスタータイル対応用スキーマ拡張
-- ============================================================================

-- raster_sources テーブル: COGファイルのソース情報を管理
CREATE TABLE IF NOT EXISTS raster_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tileset_id UUID NOT NULL REFERENCES tilesets(id) ON DELETE CASCADE,
    
    -- COGファイルのURL（Supabase Storage, S3, HTTP URL等）
    cog_url TEXT NOT NULL,
    
    -- ストレージプロバイダ
    -- 'supabase': Supabase Storage
    -- 's3': AWS S3
    -- 'http': 直接HTTPアクセス
    storage_provider VARCHAR(50) DEFAULT 'http',
    
    -- バンド情報
    band_count INTEGER,
    band_descriptions JSONB DEFAULT '[]',
    
    -- データ統計（キャッシュ用）
    statistics JSONB DEFAULT '{}',
    
    -- COGのネイティブCRS
    native_crs VARCHAR(50),
    
    -- COGのネイティブ解像度（メートル/ピクセル）
    native_resolution FLOAT,
    
    -- 推奨ズームレンジ（COGの解像度から計算）
    recommended_min_zoom INTEGER,
    recommended_max_zoom INTEGER,
    
    -- 地理的範囲（JSONB形式: [west, south, east, north]）
    bounds JSONB,
    
    -- 中心座標（JSONB形式: [lon, lat, zoom]）
    center JSONB,
    
    -- 取得日時（衛星画像等のメタデータ）
    acquisition_date TIMESTAMPTZ,
    
    -- メタデータ（追加情報）
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 1つのtilesetに1つのraster_sourceのみ（将来的に複数対応可能にするため外す可能性あり）
    UNIQUE (tileset_id)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_raster_sources_tileset_id ON raster_sources (tileset_id);
CREATE INDEX IF NOT EXISTS idx_raster_sources_storage_provider ON raster_sources (storage_provider);

-- updated_at自動更新用トリガー適用
DROP TRIGGER IF EXISTS update_raster_sources_updated_at ON raster_sources;
CREATE TRIGGER update_raster_sources_updated_at
    BEFORE UPDATE ON raster_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- コメント追加
COMMENT ON TABLE raster_sources IS 'ラスタータイルセットのCOGソース情報を管理';
COMMENT ON COLUMN raster_sources.cog_url IS 'Cloud Optimized GeoTIFFファイルのURL';
COMMENT ON COLUMN raster_sources.storage_provider IS 'ストレージプロバイダ種別';
COMMENT ON COLUMN raster_sources.band_descriptions IS 'バンドの説明（JSONBアレイ）';
COMMENT ON COLUMN raster_sources.statistics IS 'バンドごとの統計情報（min, max, mean等）';
COMMENT ON COLUMN raster_sources.bounds IS '地理的範囲 [west, south, east, north]';
COMMENT ON COLUMN raster_sources.center IS '中心座標 [lon, lat, zoom]';

-- ============================================================================
-- サンプルデータ挿入（Sentinel-2 COG）
-- ============================================================================

-- Note: サンプルデータは手動で挿入するか、seed_sample_data.pyを使用してください
