#!/usr/bin/env python3
"""
Live test script for geo-base MCP server.

Run this script to test the MCP tools against the tile server.

Usage:
    # Test against local server
    TILE_SERVER_URL=http://localhost:3000 uv run python tests/live_test.py

    # Test against production server
    TILE_SERVER_URL=https://geo-base-puce.vercel.app uv run python tests/live_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import tools
from config import get_settings
from tools.tilesets import list_tilesets, get_tileset, get_tileset_tilejson
from tools.features import search_features, get_feature


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"🔧 {title}")
    print('=' * 60)


def print_result(result: dict, indent: int = 0):
    """Print a result dictionary nicely."""
    prefix = "  " * indent
    if "error" in result:
        print(f"{prefix}❌ Error: {result['error']}")
        if "detail" in result:
            print(f"{prefix}   Detail: {result['detail'][:100]}...")
        if "hint" in result:
            print(f"{prefix}   Hint: {result['hint']}")
    else:
        for key, value in result.items():
            if isinstance(value, list):
                print(f"{prefix}📋 {key}: {len(value)} items")
            elif isinstance(value, dict):
                print(f"{prefix}📦 {key}:")
                for k, v in list(value.items())[:5]:
                    print(f"{prefix}   - {k}: {v}")
            else:
                print(f"{prefix}• {key}: {value}")


async def test_health_check():
    """Test server connection via health check."""
    print_header("Health Check")

    import httpx
    settings = get_settings()
    url = f"{settings.tile_server_url.rstrip('/')}/api/health"

    print(f"🌐 Testing: {url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            print(f"📡 Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Server is healthy")
                print_result(response.json())
                return True
            else:
                print(f"⚠️ Server returned: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_list_tilesets():
    """Test listing tilesets."""
    print_header("List Tilesets")

    result = await list_tilesets()
    print_result(result)

    if "tilesets" in result and result["tilesets"]:
        print(f"\n📦 First 5 tilesets:")
        for ts in result["tilesets"][:5]:
            print(f"   • {ts.get('name', 'unnamed')} ({ts.get('type', '?')}) - {ts.get('id', '?')[:8]}...")
        return result["tilesets"][0].get("id") if result["tilesets"] else None
    return None


async def test_get_tileset(tileset_id: str):
    """Test getting tileset details."""
    print_header(f"Get Tileset: {tileset_id[:8]}...")

    result = await get_tileset(tileset_id)
    print_result(result)
    return "error" not in result


async def test_get_tilejson(tileset_id: str):
    """Test getting TileJSON."""
    print_header(f"Get TileJSON: {tileset_id[:8]}...")

    result = await get_tileset_tilejson(tileset_id)
    print_result(result)
    return "error" not in result


async def test_search_features():
    """Test searching features."""
    print_header("Search Features (Tokyo Area)")

    # Tokyo bounding box
    bbox = "139.5,35.5,140.0,36.0"
    result = await search_features(bbox=bbox, limit=10)
    print_result(result)

    if "features" in result and result["features"]:
        print(f"\n🔍 Found features:")
        for f in result["features"][:5]:
            props = f.get("properties", {})
            name = props.get("name") or props.get("name_en") or "unnamed"
            geom_type = f.get("geometry", {}).get("type", "?")
            print(f"   • {name} ({geom_type})")
        return result["features"][0].get("id") if result["features"] else None
    return None


async def test_get_feature(feature_id: str):
    """Test getting feature details."""
    print_header(f"Get Feature: {feature_id[:8]}...")

    result = await get_feature(feature_id)
    print_result(result)
    return "error" not in result


async def main():
    """Run all tests."""
    settings = get_settings()

    print("\n" + "=" * 60)
    print("🧪 geo-base MCP Server Live Tests")
    print("=" * 60)
    print(f"📡 Tile Server: {settings.tile_server_url}")
    print(f"🔐 API Token: {'configured' if settings.api_token else 'not configured'}")
    print(f"🌍 Environment: {settings.environment}")

    # Test health check first
    healthy = await test_health_check()
    if not healthy:
        print("\n" + "=" * 60)
        print("⚠️  Server not accessible. Check:")
        print("   1. Is the tile server running?")
        print("   2. Is TILE_SERVER_URL correct?")
        print("   3. Are there any network restrictions?")
        print("=" * 60)
        return

    # Test tileset operations
    tileset_id = await test_list_tilesets()
    if tileset_id:
        await test_get_tileset(tileset_id)
        await test_get_tilejson(tileset_id)

    # Test feature operations
    feature_id = await test_search_features()
    if feature_id:
        await test_get_feature(feature_id)

    print("\n" + "=" * 60)
    print("✅ Live tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
