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

-- ============================================================================
-- サンプルデータ挿入（Sentinel-2 COG）
-- ============================================================================

-- サンプルラスタータイルセットを作成
INSERT INTO tilesets (name, description, type, format, min_zoom, max_zoom, is_public, metadata)
VALUES (
    'sentinel2-sample',
    'Sentinel-2 Sample COG (Tokyo Area)',
    'raster',
    'png',
    6,
    14,
    true,
    '{
        "source": "Sentinel-2 L2A",
        "bands": "1,2,3",
        "scale_min": 0,
        "scale_max": 3000,
        "description": "RGB composite from Sentinel-2 satellite imagery"
    }'::jsonb
)
ON CONFLICT DO NOTHING
RETURNING id;

-- サンプルCOGソースを登録（上記で作成したtilesetのIDを使用）
-- Note: 実際のデプロイ時は、このURLを自分のCOGファイルに置き換えてください
DO $$
DECLARE
    v_tileset_id UUID;
BEGIN
    -- サンプルtilesetのIDを取得
    SELECT id INTO v_tileset_id FROM tilesets WHERE name = 'sentinel2-sample' LIMIT 1;
    
    IF v_tileset_id IS NOT NULL THEN
        INSERT INTO raster_sources (
            tileset_id,
            cog_url,
            storage_provider,
            band_count,
            band_descriptions,
            native_crs,
            recommended_min_zoom,
            recommended_max_zoom,
            metadata
        )
        VALUES (
            v_tileset_id,
            'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/54/T/WN/2023/11/S2B_54TWN_20231118_1_L2A/TCI.tif',
            's3',
            3,
            '["Red", "Green", "Blue"]'::jsonb,
            'EPSG:32654',
            6,
            14,
            '{
                "satellite": "Sentinel-2B",
                "processing_level": "L2A",
                "tile_id": "54TWN",
                "date": "2023-11-18",
                "product": "True Color Image (TCI)"
            }'::jsonb
        )
        ON CONFLICT (tileset_id) DO UPDATE
        SET cog_url = EXCLUDED.cog_url,
            updated_at = NOW();
        
        RAISE NOTICE 'Raster source created for tileset: %', v_tileset_id;
    ELSE
        RAISE NOTICE 'Sample tileset not found';
    END IF;
END $$;

-- ============================================================================
-- 便利なビュー作成
-- ============================================================================

-- ラスタータイルセット一覧ビュー
CREATE OR REPLACE VIEW raster_tilesets_view AS
SELECT 
    t.id,
    t.name,
    t.description,
    t.format,
    t.min_zoom,
    t.max_zoom,
    t.is_public,
    t.attribution,
    t.metadata,
    rs.cog_url,
    rs.storage_provider,
    rs.band_count,
    rs.band_descriptions,
    rs.native_crs,
    rs.recommended_min_zoom,
    rs.recommended_max_zoom,
    rs.acquisition_date,
    t.created_at,
    t.updated_at
FROM tilesets t
JOIN raster_sources rs ON rs.tileset_id = t.id
WHERE t.type = 'raster';

COMMENT ON VIEW raster_tilesets_view IS 'ラスタータイルセットとそのソース情報を結合したビュー';
