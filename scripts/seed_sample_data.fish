#!/usr/bin/env fish
#
# geo-base サンプルデータ投入スクリプト (fish shell)
#
# 使用方法:
#   # 環境変数を設定してから実行
#   set -x API_URL http://localhost:8000
#   set -x AUTH_TOKEN (curl -sS -X POST $API_URL/api/auth/login \
#       -H "Content-Type: application/json" \
#       -d '{"email":"<your-email>","password":"<your-password>"}' \
#       | jq -r .access_token)
#   fish scripts/seed_sample_data.fish
#
# トークンは POST /api/auth/login で取得する（AUTH_PROVIDER=local）。

# 設定
set API_URL (test -n "$API_URL"; and echo $API_URL; or echo "http://localhost:8000")
set AUTH_TOKEN (test -n "$AUTH_TOKEN"; and echo $AUTH_TOKEN; or echo "")

if test -z "$AUTH_TOKEN"
    echo "❌ AUTH_TOKEN が設定されていません"
    echo ""
    echo "使用方法:"
    echo "  set -x AUTH_TOKEN (curl -sS -X POST \$API_URL/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"<email>\",\"password\":\"<pw>\"}' | jq -r .access_token)"
    echo "  fish scripts/seed_sample_data.fish"
    exit 1
end

echo "========================================"
echo "geo-base サンプルデータ投入"
echo "========================================"
echo "API URL: $API_URL"
echo ""

# ヘルスチェック
echo "🔍 ヘルスチェック..."
set health_status (curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/health")
if test "$health_status" != "200"
    echo "❌ API に接続できません (status: $health_status)"
    exit 1
end
echo "✅ API 接続OK"
echo ""

# 共通ヘッダー
set HEADERS -H "Content-Type: application/json" -H "Authorization: Bearer $AUTH_TOKEN"

# ========================================
# 1. タイルセット作成: 東京ランドマーク
# ========================================
echo "📦 タイルセット '東京ランドマーク' を作成中..."
set tileset1_response (curl -s -X POST "$API_URL/api/tilesets" \
    $HEADERS \
    -d '{
        "name": "東京ランドマーク",
        "description": "東京の主要ランドマーク（POI）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 12],
        "is_public": true
    }')

set tileset1_id (echo $tileset1_response | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if test -n "$tileset1_id"
    echo "   ✅ 作成完了: $tileset1_id"
else
    echo "   ⚠️ 作成失敗または既存: $tileset1_response"
    # 既存のタイルセットIDを取得
    set existing (curl -s "$API_URL/api/tilesets" $HEADERS)
    set tileset1_id (echo $existing | grep -o '"id":"[^"]*"[^}]*"name":"東京ランドマーク"' | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    if test -n "$tileset1_id"
        echo "   📌 既存ID: $tileset1_id"
    end
end
echo ""

# ========================================
# 2. タイルセット作成: 東京鉄道路線
# ========================================
echo "📦 タイルセット '東京鉄道路線' を作成中..."
set tileset2_response (curl -s -X POST "$API_URL/api/tilesets" \
    $HEADERS \
    -d '{
        "name": "東京鉄道路線",
        "description": "東京の主要鉄道路線（LineString）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 11],
        "is_public": true
    }')

set tileset2_id (echo $tileset2_response | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if test -n "$tileset2_id"
    echo "   ✅ 作成完了: $tileset2_id"
else
    echo "   ⚠️ 作成失敗または既存"
end
echo ""

# ========================================
# 3. タイルセット作成: 東京エリア
# ========================================
echo "📦 タイルセット '東京エリア' を作成中..."
set tileset3_response (curl -s -X POST "$API_URL/api/tilesets" \
    $HEADERS \
    -d '{
        "name": "東京エリア",
        "description": "東京の主要エリア境界（Polygon）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 11],
        "is_public": true
    }')

set tileset3_id (echo $tileset3_response | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if test -n "$tileset3_id"
    echo "   ✅ 作成完了: $tileset3_id"
else
    echo "   ⚠️ 作成失敗または既存"
end
echo ""

# ========================================
# 4. フィーチャー追加: POI
# ========================================
if test -n "$tileset1_id"
    echo "📍 東京ランドマークにPOIを追加中..."
    
    # 東京駅
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset1_id\", \"layer_name\": \"landmarks\", \"properties\": {\"name\": \"東京駅\", \"type\": \"station\"}, \"geometry\": {\"type\": \"Point\", \"coordinates\": [139.7671, 35.6812]}}" > /dev/null
    echo "   ✅ 東京駅"
    
    # 東京タワー
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset1_id\", \"layer_name\": \"landmarks\", \"properties\": {\"name\": \"東京タワー\", \"type\": \"tower\", \"height\": 333}, \"geometry\": {\"type\": \"Point\", \"coordinates\": [139.7454, 35.6586]}}" > /dev/null
    echo "   ✅ 東京タワー"
    
    # スカイツリー
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset1_id\", \"layer_name\": \"landmarks\", \"properties\": {\"name\": \"東京スカイツリー\", \"type\": \"tower\", \"height\": 634}, \"geometry\": {\"type\": \"Point\", \"coordinates\": [139.8107, 35.7101]}}" > /dev/null
    echo "   ✅ 東京スカイツリー"
    
    # 渋谷
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset1_id\", \"layer_name\": \"landmarks\", \"properties\": {\"name\": \"渋谷スクランブル交差点\", \"type\": \"intersection\"}, \"geometry\": {\"type\": \"Point\", \"coordinates\": [139.7006, 35.6595]}}" > /dev/null
    echo "   ✅ 渋谷スクランブル交差点"
    
    # 新宿駅
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset1_id\", \"layer_name\": \"landmarks\", \"properties\": {\"name\": \"新宿駅\", \"type\": \"station\"}, \"geometry\": {\"type\": \"Point\", \"coordinates\": [139.7003, 35.6897]}}" > /dev/null
    echo "   ✅ 新宿駅"
    
    echo ""
end

# ========================================
# 5. フィーチャー追加: LineString
# ========================================
if test -n "$tileset2_id"
    echo "📍 東京鉄道路線にLineStringを追加中..."
    
    # 山手線（一部）
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset2_id\", \"layer_name\": \"railways\", \"properties\": {\"name\": \"山手線（東京-池袋）\", \"type\": \"JR\", \"color\": \"#9ACD32\"}, \"geometry\": {\"type\": \"LineString\", \"coordinates\": [[139.7671, 35.6812], [139.7746, 35.6853], [139.7730, 35.6917], [139.7774, 35.7078], [139.7710, 35.7281], [139.7103, 35.7287]]}}" > /dev/null
    echo "   ✅ 山手線（東京-池袋）"
    
    # 中央線
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset2_id\", \"layer_name\": \"railways\", \"properties\": {\"name\": \"中央線（東京-新宿）\", \"type\": \"JR\", \"color\": \"#FF4500\"}, \"geometry\": {\"type\": \"LineString\", \"coordinates\": [[139.7671, 35.6812], [139.7580, 35.6848], [139.7440, 35.7019], [139.7200, 35.6909], [139.7003, 35.6897]]}}" > /dev/null
    echo "   ✅ 中央線（東京-新宿）"
    
    echo ""
end

# ========================================
# 6. フィーチャー追加: Polygon
# ========================================
if test -n "$tileset3_id"
    echo "📍 東京エリアにPolygonを追加中..."
    
    # 千代田区
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset3_id\", \"layer_name\": \"areas\", \"properties\": {\"name\": \"千代田区\", \"type\": \"ward\"}, \"geometry\": {\"type\": \"Polygon\", \"coordinates\": [[[139.74, 35.67], [139.78, 35.67], [139.78, 35.70], [139.74, 35.70], [139.74, 35.67]]]}}" > /dev/null
    echo "   ✅ 千代田区"
    
    # 中央区
    curl -s -X POST "$API_URL/api/features" $HEADERS \
        -d "{\"tileset_id\": \"$tileset3_id\", \"layer_name\": \"areas\", \"properties\": {\"name\": \"中央区\", \"type\": \"ward\"}, \"geometry\": {\"type\": \"Polygon\", \"coordinates\": [[[139.76, 35.65], [139.79, 35.65], [139.79, 35.68], [139.76, 35.68], [139.76, 35.65]]]}}" > /dev/null
    echo "   ✅ 中央区"
    
    echo ""
end

# ========================================
# 完了
# ========================================
echo "========================================"
echo "✅ サンプルデータ投入完了"
echo "========================================"
echo ""
echo "📌 確認用URL:"
echo "   タイルセット一覧: $API_URL/api/tilesets"
echo "   フィーチャー一覧: $API_URL/api/features"
echo ""
echo "📌 Admin UI:"
echo "   http://localhost:3000/tilesets"
echo "   http://localhost:3000/features"
