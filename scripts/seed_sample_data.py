#!/usr/bin/env python3
"""
geo-base サンプルデータ投入スクリプト

このスクリプトは以下を行います：
1. vector タイプのタイルセットを作成
2. サンプルフィーチャー（POI、線、ポリゴン）を投入

使用方法:
  # ローカル環境
  python scripts/seed_sample_data.py --api-url http://localhost:8000 --token YOUR_SUPABASE_TOKEN

  # 本番環境
  python scripts/seed_sample_data.py --api-url https://geo-base-api.fly.dev --token YOUR_SUPABASE_TOKEN

トークンの取得方法:
  1. ブラウザで geo-base-app にログイン
  2. 開発者ツール > Application > Local Storage > supabase.auth.token
  3. access_token の値をコピー
"""

import argparse
import json
import requests
from typing import Optional

# サンプルタイルセットの定義
SAMPLE_TILESETS = [
    {
        "name": "東京ランドマーク",
        "description": "東京の主要ランドマーク（POI）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 12],
        "is_public": True,
        "metadata": {"category": "landmarks", "region": "tokyo"}
    },
    {
        "name": "東京鉄道路線",
        "description": "東京の主要鉄道路線（LineString）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 11],
        "is_public": True,
        "metadata": {"category": "railways", "region": "tokyo"}
    },
    {
        "name": "東京エリア",
        "description": "東京の主要エリア境界（Polygon）",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 35.9],
        "center": [139.7671, 35.6812, 11],
        "is_public": True,
        "metadata": {"category": "areas", "region": "tokyo"}
    }
]

# サンプルフィーチャーの定義
SAMPLE_FEATURES = {
    "東京ランドマーク": [
        {
            "layer_name": "landmarks",
            "properties": {"name": "東京駅", "type": "station", "lines": ["JR", "丸ノ内線"]},
            "geometry": {"type": "Point", "coordinates": [139.7671, 35.6812]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "東京タワー", "type": "tower", "height": 333},
            "geometry": {"type": "Point", "coordinates": [139.7454, 35.6586]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "東京スカイツリー", "type": "tower", "height": 634},
            "geometry": {"type": "Point", "coordinates": [139.8107, 35.7101]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "渋谷スクランブル交差点", "type": "intersection"},
            "geometry": {"type": "Point", "coordinates": [139.7006, 35.6595]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "新宿駅", "type": "station", "lines": ["JR", "小田急", "京王", "丸ノ内線"]},
            "geometry": {"type": "Point", "coordinates": [139.7003, 35.6897]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "皇居", "type": "palace"},
            "geometry": {"type": "Point", "coordinates": [139.7528, 35.6852]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "浅草寺", "type": "temple"},
            "geometry": {"type": "Point", "coordinates": [139.7966, 35.7148]}
        },
        {
            "layer_name": "landmarks",
            "properties": {"name": "上野動物園", "type": "zoo"},
            "geometry": {"type": "Point", "coordinates": [139.7714, 35.7163]}
        }
    ],
    "東京鉄道路線": [
        {
            "layer_name": "railways",
            "properties": {"name": "山手線（東側）", "type": "JR", "color": "#9ACD32"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [139.7671, 35.6812],  # 東京
                    [139.7746, 35.6853],  # 神田
                    [139.7730, 35.6917],  # 秋葉原
                    [139.7774, 35.7078],  # 上野
                    [139.7816, 35.7219],  # 鶯谷
                    [139.7710, 35.7281],  # 日暮里
                    [139.7587, 35.7315],  # 西日暮里
                    [139.7486, 35.7330],  # 田端
                    [139.7383, 35.7365],  # 駒込
                    [139.7286, 35.7281],  # 巣鴨
                    [139.7195, 35.7220],  # 大塚
                    [139.7103, 35.7287],  # 池袋
                ]
            }
        },
        {
            "layer_name": "railways",
            "properties": {"name": "中央線（東京-新宿）", "type": "JR", "color": "#FF4500"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [139.7671, 35.6812],  # 東京
                    [139.7630, 35.6814],  # 神田方面
                    [139.7580, 35.6848],  # 御茶ノ水
                    [139.7505, 35.6987],  # 水道橋
                    [139.7440, 35.7019],  # 飯田橋
                    [139.7302, 35.7048],  # 市ヶ谷
                    [139.7200, 35.6909],  # 四ツ谷
                    [139.7103, 35.6812],  # 信濃町
                    [139.7003, 35.6897],  # 新宿
                ]
            }
        },
        {
            "layer_name": "railways",
            "properties": {"name": "銀座線", "type": "Metro", "color": "#FF8C00"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [139.7006, 35.6595],  # 渋谷
                    [139.7103, 35.6647],  # 表参道
                    [139.7267, 35.6700],  # 青山一丁目
                    [139.7384, 35.6702],  # 赤坂見附
                    [139.7505, 35.6748],  # 溜池山王
                    [139.7594, 35.6714],  # 虎ノ門
                    [139.7636, 35.6718],  # 新橋
                    [139.7648, 35.6751],  # 銀座
                    [139.7704, 35.6813],  # 京橋
                    [139.7714, 35.6866],  # 日本橋
                    [139.7739, 35.6920],  # 三越前
                    [139.7746, 35.6983],  # 神田
                    [139.7819, 35.7024],  # 末広町
                    [139.7880, 35.7083],  # 上野広小路
                    [139.7838, 35.7117],  # 上野
                    [139.8022, 35.7113],  # 稲荷町
                    [139.7966, 35.7148],  # 浅草
                ]
            }
        }
    ],
    "東京エリア": [
        {
            "layer_name": "areas",
            "properties": {"name": "千代田区", "type": "ward", "population": 67000},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [139.7400, 35.6700],
                    [139.7800, 35.6700],
                    [139.7800, 35.7000],
                    [139.7400, 35.7000],
                    [139.7400, 35.6700]
                ]]
            }
        },
        {
            "layer_name": "areas",
            "properties": {"name": "中央区", "type": "ward", "population": 170000},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [139.7600, 35.6500],
                    [139.7900, 35.6500],
                    [139.7900, 35.6800],
                    [139.7600, 35.6800],
                    [139.7600, 35.6500]
                ]]
            }
        },
        {
            "layer_name": "areas",
            "properties": {"name": "渋谷エリア", "type": "area", "description": "渋谷駅周辺"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [139.6950, 35.6550],
                    [139.7100, 35.6550],
                    [139.7100, 35.6650],
                    [139.6950, 35.6650],
                    [139.6950, 35.6550]
                ]]
            }
        }
    ]
}


class GeoBaseClient:
    """geo-base API クライアント"""
    
    def __init__(self, api_url: str, token: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            resp = requests.get(f"{self.api_url}/api/health")
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ ヘルスチェック失敗: {e}")
            return False
    
    def list_tilesets(self) -> list:
        """タイルセット一覧を取得"""
        resp = requests.get(f"{self.api_url}/api/tilesets", headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "tilesets" in data:
            return data["tilesets"]
        return []
    
    def create_tileset(self, tileset_data: dict) -> dict:
        """タイルセットを作成"""
        resp = requests.post(
            f"{self.api_url}/api/tilesets",
            headers=self.headers,
            json=tileset_data
        )
        resp.raise_for_status()
        return resp.json()
    
    def create_feature(self, feature_data: dict) -> dict:
        """フィーチャーを作成"""
        resp = requests.post(
            f"{self.api_url}/api/features",
            headers=self.headers,
            json=feature_data
        )
        resp.raise_for_status()
        return resp.json()
    
    def list_features(self, tileset_id: Optional[str] = None, limit: int = 100) -> list:
        """フィーチャー一覧を取得"""
        params = {"limit": limit}
        if tileset_id:
            params["tileset_id"] = tileset_id
        resp = requests.get(
            f"{self.api_url}/api/features",
            headers=self.headers,
            params=params
        )
        resp.raise_for_status()
        return resp.json()


def main():
    parser = argparse.ArgumentParser(description="geo-base サンプルデータ投入スクリプト")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--token", required=True, help="Supabase access token")
    parser.add_argument("--dry-run", action="store_true", help="実際には作成しない")
    args = parser.parse_args()
    
    print("=" * 60)
    print("geo-base サンプルデータ投入スクリプト")
    print("=" * 60)
    print(f"API URL: {args.api_url}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    client = GeoBaseClient(args.api_url, args.token)
    
    # ヘルスチェック
    print("🔍 ヘルスチェック...")
    if not client.health_check():
        print("❌ API に接続できません")
        return 1
    print("✅ API 接続OK")
    print()
    
    # 既存タイルセットを確認
    print("🔍 既存タイルセットを確認...")
    existing_tilesets = client.list_tilesets()
    existing_names = {ts["name"] for ts in existing_tilesets}
    print(f"   既存: {len(existing_tilesets)} 件")
    print()
    
    # タイルセット作成
    created_tilesets = {}
    for ts_data in SAMPLE_TILESETS:
        name = ts_data["name"]
        if name in existing_names:
            print(f"⏭️  タイルセット '{name}' は既に存在します（スキップ）")
            # 既存のタイルセットIDを取得
            for ts in existing_tilesets:
                if ts["name"] == name:
                    created_tilesets[name] = ts["id"]
                    break
            continue
        
        if args.dry_run:
            print(f"🔹 [DRY RUN] タイルセット '{name}' を作成")
            created_tilesets[name] = "dry-run-id"
        else:
            print(f"📦 タイルセット '{name}' を作成中...")
            try:
                result = client.create_tileset(ts_data)
                created_tilesets[name] = result["id"]
                print(f"   ✅ 作成完了: {result['id']}")
            except Exception as e:
                print(f"   ❌ 作成失敗: {e}")
                continue
    
    print()
    
    # フィーチャー作成
    total_features = 0
    for tileset_name, features in SAMPLE_FEATURES.items():
        tileset_id = created_tilesets.get(tileset_name)
        if not tileset_id:
            print(f"⚠️  タイルセット '{tileset_name}' が見つかりません（スキップ）")
            continue
        
        print(f"📍 タイルセット '{tileset_name}' にフィーチャーを追加中...")
        
        for feature_data in features:
            feature_data["tileset_id"] = tileset_id
            feature_name = feature_data["properties"].get("name", "unnamed")
            
            if args.dry_run:
                print(f"   🔹 [DRY RUN] フィーチャー '{feature_name}' を作成")
            else:
                try:
                    result = client.create_feature(feature_data)
                    print(f"   ✅ '{feature_name}' 作成完了")
                    total_features += 1
                except Exception as e:
                    print(f"   ❌ '{feature_name}' 作成失敗: {e}")
    
    print()
    print("=" * 60)
    print(f"✅ 完了: タイルセット {len(created_tilesets)} 件, フィーチャー {total_features} 件")
    print("=" * 60)
    
    # 確認用URL
    print()
    print("📌 確認用URL:")
    print(f"   タイルセット一覧: {args.api_url}/api/tilesets")
    print(f"   フィーチャー一覧: {args.api_url}/api/features")
    for name, tileset_id in created_tilesets.items():
        if tileset_id != "dry-run-id":
            print(f"   {name}: {args.api_url}/api/tilesets/{tileset_id}")
    
    return 0


if __name__ == "__main__":
    exit(main())
