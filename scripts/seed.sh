#!/bin/bash

# geo-base Seed Script
# This script inserts sample data for testing

set -e

echo "🌱 Seeding geo-base database..."

# Database connection parameters
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-geo_base}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}

export PGPASSWORD=$DB_PASSWORD

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "⚠️  psql not found. Using docker exec instead..."
    PSQL_CMD="docker exec -i geo-base-postgis psql -U $DB_USER -d $DB_NAME"
else
    PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
fi

# Insert sample tileset
echo "📦 Creating sample tileset..."
$PSQL_CMD << 'EOF'
INSERT INTO tilesets (name, description, type, format, min_zoom, max_zoom, is_public)
VALUES 
    ('sample-vector', 'Sample vector tileset for testing', 'vector', 'pbf', 0, 14, true),
    ('sample-raster', 'Sample raster tileset for testing', 'raster', 'png', 0, 18, true)
ON CONFLICT DO NOTHING;
EOF

# Insert sample features (Tokyo area points of interest)
echo "📍 Creating sample features..."
$PSQL_CMD << 'EOF'
-- Get the sample-vector tileset ID
DO $$
DECLARE
    v_tileset_id UUID;
BEGIN
    SELECT id INTO v_tileset_id FROM tilesets WHERE name = 'sample-vector' LIMIT 1;
    
    IF v_tileset_id IS NOT NULL THEN
        -- Insert sample features (Tokyo landmarks)
        INSERT INTO features (tileset_id, layer_name, geom, properties)
        VALUES
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.7671, 35.6812), 4326), 
             '{"name": "東京駅", "name_en": "Tokyo Station", "type": "station"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.7454, 35.6586), 4326), 
             '{"name": "東京タワー", "name_en": "Tokyo Tower", "type": "landmark"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.8107, 35.7101), 4326), 
             '{"name": "東京スカイツリー", "name_en": "Tokyo Skytree", "type": "landmark"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.6917, 35.6895), 4326), 
             '{"name": "新宿駅", "name_en": "Shinjuku Station", "type": "station"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.7016, 35.6580), 4326), 
             '{"name": "渋谷駅", "name_en": "Shibuya Station", "type": "station"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.7745, 35.7148), 4326), 
             '{"name": "浅草寺", "name_en": "Senso-ji Temple", "type": "temple"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.7528, 35.6762), 4326), 
             '{"name": "皇居", "name_en": "Imperial Palace", "type": "landmark"}'::jsonb),
            (v_tileset_id, 'landmarks', ST_SetSRID(ST_MakePoint(139.6999, 35.6762), 4326), 
             '{"name": "明治神宮", "name_en": "Meiji Shrine", "type": "shrine"}'::jsonb)
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Sample features created for tileset: %', v_tileset_id;
    ELSE
        RAISE NOTICE 'No tileset found';
    END IF;
END $$;
EOF

echo ""
echo "✅ Seeding complete!"
echo ""
echo "You can view the data with:"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c 'SELECT * FROM tilesets;'"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c 'SELECT id, layer_name, properties FROM features;'"
