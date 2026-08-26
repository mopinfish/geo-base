# MCPサーバー開発 ベストプラクティス & デザインパターン

**作成日**: 2025-12-14  
**参考資料**: 
- Anthropic公式クイックスタート（quickstart-resources.txt）
- MCPサーバー開発大全（openweather-mcp.txt, chillax-mcp-server.txt, documentor.txt）

---

## 1. 概要

本ドキュメントは、「MCPサーバー開発大全」のサンプルコードおよびAnthropic公式サンプルから抽出した、MCPサーバー開発のベストプラクティスとデザインパターンをまとめたものです。

---

## 2. プロジェクト構成パターン

### 2.1 基本ディレクトリ構成

```
mcp-server/
├── server.py           # エントリーポイント（FastMCPインスタンス）
├── config.py           # 設定管理
├── main.py             # CLIエントリーポイント（オプション）
├── tools/              # ツール実装（機能別に分割）
│   ├── __init__.py
│   └── *.py
├── tests/              # テストコード
│   ├── conftest.py     # pytest設定
│   └── test_*.py
├── pyproject.toml      # 依存関係管理
├── uv.lock             # 依存関係ロック
├── README.md           # ドキュメント
├── .env.example        # 環境変数サンプル
└── Dockerfile          # コンテナ化（オプション）
```

### 2.2 pyproject.toml テンプレート

```toml
[project]
name = "my-mcp-server"
version = "0.1.0"
description = "My MCP Server description"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Author Name"}]
keywords = ["mcp", "api", "server"]

dependencies = [
    "fastmcp>=0.1.0",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[tool.ruff]
line-length = 120
target-version = "py310"
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## 3. FastMCPサーバーパターン

### 3.1 基本的なサーバー初期化

**出典**: weather-server-python/weather.py

```python
from mcp.server.fastmcp import FastMCP

# サーバーインスタンスの作成
mcp = FastMCP("server-name")

# ツールの定義
@mcp.tool()
async def my_tool(param: str) -> str:
    """ツールの説明（Claudeに表示される）
    
    Args:
        param: パラメータの説明
    """
    return f"Result: {param}"

# エントリーポイント
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 3.2 複数トランスポート対応

**出典**: geo-base/mcp/server.py

```python
import os

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    if transport == "stdio":
        mcp.run()
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        print(f"Unknown transport: {transport}")
        exit(1)
```

---

## 4. 設定管理パターン

### 4.1 環境変数による設定

**出典**: openweather-mcp.txt

```python
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数から設定を取得
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = os.getenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5")

# APIキーが設定されているかチェック
if not API_KEY:
    raise ValueError(
        "OPENWEATHER_API_KEY is not set. "
        "Please create a .env file with your API key."
    )
```

### 4.2 Pydantic Settings による型安全な設定

**推奨パターン**:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # 必須設定
    api_url: str
    
    # オプション設定（デフォルト値あり）
    api_token: str | None = None
    http_timeout: float = 30.0
    environment: str = "development"
    
    # サーバー設定
    server_name: str = "my-mcp-server"
    server_version: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンを取得"""
    return Settings()
```

---

## 5. ツール実装パターン

### 5.1 基本的なツール実装

**出典**: openweather-mcp.txt

```python
@mcp.tool()
async def get_weather(city: str) -> str:
    """
    指定された都市の現在の天気を取得します
    
    Args:
        city: 都市名（例: Tokyo, London, New York）
        
    Returns:
        天気情報のフォーマットされた文字列
    """
    # 入力の検証
    if not city or not city.strip():
        return "エラー: 都市名を入力してください。"
    
    # データ取得
    weather_data = await fetch_weather_data(city.strip())
    
    # エラーハンドリング
    if weather_data is None:
        return f"すみません。'{city}' の天気情報を取得できませんでした。"
    
    # フォーマットして返す
    return format_weather_response(weather_data)
```

### 5.2 カスケード処理パターン

**出典**: chillax-mcp-server.txt

複数のAPI呼び出しを連鎖させるパターン：

```python
@mcp.tool()
async def get_activity_suggestion(city: str, days_ahead: int = 0) -> dict:
    """
    都市と日付を指定して、天気に基づいた過ごし方を提案
    
    Args:
        city: 都市名
        days_ahead: 何日後か（0-5）
    
    Returns:
        天気情報と動画提案を含む完全な結果
    """
    # Step 1: 天気情報を取得
    weather_info = await get_weather_forecast(city, days_ahead)
    
    if "error" in weather_info:
        return weather_info
    
    # Step 2: 天気に基づいて動画を提案
    video_suggestions = await suggest_videos(weather_info)
    
    # 結果を統合
    return {
        "weather": weather_info,
        "suggestions": video_suggestions,
    }
```

### 5.3 辞書ベースのパラメータ・レスポンス

**出典**: geo-base/mcp/tools/

```python
async def search_features(
    bbox: str | None = None,
    layer: str | None = None,
    filter: str | None = None,
    limit: int = 100,
    tileset_id: str | None = None,
) -> dict:
    """
    フィーチャーを検索
    
    Returns:
        Dictionary containing:
        - features: List of GeoJSON features
        - count: Number of features returned
        - total: Total count of matching features
    """
    params = {"limit": limit}
    
    if bbox:
        params["bbox"] = bbox
    if layer:
        params["layer"] = layer
    if filter:
        params["filter"] = filter
    if tileset_id:
        params["tileset_id"] = tileset_id
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/features", params=params)
        return response.json()
```

---

## 6. HTTPクライアントパターン

### 6.1 基本的なHTTP通信

**出典**: weather-server-python/weather.py

```python
import httpx
from typing import Any

async def make_api_request(url: str) -> dict[str, Any] | None:
    """APIリクエストを実行（適切なエラーハンドリング付き）"""
    headers = {
        "User-Agent": "my-app/1.0",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
```

### 6.2 詳細なエラーハンドリング

**出典**: openweather-mcp.txt

```python
async def fetch_data(url: str, params: dict) -> dict | None:
    """詳細なエラーハンドリング付きのデータ取得"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"Not found: {url}")
            elif e.response.status_code == 401:
                print("Invalid API key")
            else:
                print(f"HTTP error: {e}")
            return None
        except httpx.TimeoutException:
            print(f"Timeout: {url}")
            return None
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
```

### 6.3 認証ヘッダー付きリクエスト

**出典**: geo-base/mcp/tools/crud.py

```python
def _get_headers() -> dict:
    """認証トークンを含むHTTPヘッダーを取得"""
    headers = {
        "Content-Type": "application/json",
    }
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"
    return headers

async def create_resource(data: dict) -> dict:
    """認証付きPOSTリクエスト"""
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.post(
                f"{API_URL}/api/resources",
                json=data,
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required."}
            if response.status_code == 403:
                return {"error": "Not authorized."}
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error {e.response.status_code}"}
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}
```

---

## 7. レスポンスフォーマットパターン

### 7.1 人間が読みやすいフォーマット

**出典**: openweather-mcp.txt

```python
def format_weather_response(data: dict) -> str:
    """天気データを読みやすい形式にフォーマット"""
    city_name = data.get("name", "不明")
    country = data.get("sys", {}).get("country", "")
    
    weather = data.get("weather", [{}])[0]
    description = weather.get("description", "不明")
    
    main = data.get("main", {})
    temp = main.get("temp", 0)
    humidity = main.get("humidity", 0)
    
    response = f"""
{city_name}, {country} の現在の天気

天候: {description}
現在の気温: {temp:.1f}°C
湿度: {humidity}%
"""
    return response.strip()
```

### 7.2 構造化されたレスポンス

**推奨パターン**:

```python
def create_response(
    data: Any,
    success: bool = True,
    message: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """標準化されたレスポンス構造を作成"""
    response = {
        "success": success,
        "data": data,
    }
    
    if message:
        response["message"] = message
    if metadata:
        response["metadata"] = metadata
    
    return response

def create_error_response(
    error: str,
    code: str | None = None,
    details: dict | None = None,
) -> dict:
    """標準化されたエラーレスポンスを作成"""
    response = {
        "success": False,
        "error": error,
    }
    
    if code:
        response["error_code"] = code
    if details:
        response["details"] = details
    
    return response
```

---

## 8. データ構造パターン

### 8.1 dataclassによる型定義

**出典**: documentor.txt

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class DocumentSection:
    """ドキュメントのセクション情報"""
    title: str
    content: str
    level: int
    file_path: str
    line_number: int

@dataclass
class SearchResult:
    """検索結果"""
    file: str
    title: str
    content: str
    relevance: float
```

### 8.2 Enumによる定数定義

**出典**: chillax-mcp-server.txt

```python
from enum import Enum

class WeatherCondition(Enum):
    PERFECT = "perfect"
    HOT = "hot"
    COLD = "cold"
    RAINY = "rainy"
    STORMY = "stormy"

class Language(Enum):
    JA = "ja"
    EN = "en"
    KO = "ko"
    ZH = "zh"
```

### 8.3 マッピング辞書

**出典**: chillax-mcp-server.txt

```python
# 都市名から言語を推測するマッピング
CITY_LANGUAGE_MAP = {
    "tokyo": Language.JA,
    "osaka": Language.JA,
    "london": Language.EN,
    "new york": Language.EN,
    "seoul": Language.KO,
    "beijing": Language.ZH,
}

# 天気条件に応じた検索クエリテンプレート
SEARCH_QUERIES = {
    WeatherCondition.PERFECT: {
        Language.JA: ["アウトドア vlog", "公園 散歩"],
        Language.EN: ["outdoor activities", "park walking"],
    },
    WeatherCondition.RAINY: {
        Language.JA: ["雨の日 過ごし方", "ジャズ BGM"],
        Language.EN: ["rainy day activities", "jazz music"],
    },
}
```

---

## 9. インデックス・検索パターン

### 9.1 ドキュメントインデックス

**出典**: documentor.txt

```python
class DocumentIndexer:
    """ドキュメントのインデックス化を行うクラス"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.documents: Dict[str, List[DocumentSection]] = {}
    
    def index_all_documents(self):
        """すべてのドキュメントをインデックス化"""
        md_files = list(self.repo_path.rglob("*.md"))
        for md_file in md_files:
            if ".git" not in str(md_file):
                self._index_markdown(md_file)
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """ドキュメントを検索"""
        query_lower = query.lower()
        results = []
        
        for file_path, sections in self.documents.items():
            for section in sections:
                if (query_lower in section.title.lower() or 
                    query_lower in section.content.lower()):
                    results.append({
                        "file": file_path,
                        "title": section.title,
                        "content": section.content[:200] + "...",
                        "relevance": self._calculate_relevance(query_lower, section)
                    })
        
        # 関連度でソート
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:5]
    
    def _calculate_relevance(self, query: str, section: DocumentSection) -> float:
        """関連度を計算"""
        score = 0.0
        
        # タイトルに含まれる場合は高スコア
        if query in section.title.lower():
            score += 2.0
        
        # 内容に含まれる回数をカウント
        score += section.content.lower().count(query) * 0.1
        
        return score
```

---

## 10. テストパターン

### 10.1 pytest設定

**出典**: geo-base/mcp/tests/conftest.py

```python
import sys
import os
from pathlib import Path

# パスの設定
sys.path.insert(0, str(Path(__file__).parent.parent))

# テスト環境変数の設定
os.environ.setdefault("API_URL", "https://api.example.com")
os.environ.setdefault("ENVIRONMENT", "test")

# 特定ファイルをテスト対象から除外
collect_ignore = ["live_test.py"]

def pytest_configure(config):
    """pytest設定"""
    print("\n" + "=" * 60)
    print("🧪 MCP Server Tests")
    print(f"📡 API URL: {os.environ.get('API_URL')}")
    print("=" * 60)
```

### 10.2 非同期テスト

```python
import pytest
from tools.geocoding import geocode, reverse_geocode

@pytest.mark.asyncio
async def test_geocode_tokyo():
    """東京のジオコーディングテスト"""
    result = await geocode(query="東京駅")
    
    assert "results" in result
    assert result["count"] > 0
    
    first_result = result["results"][0]
    assert "latitude" in first_result
    assert "longitude" in first_result
    # 東京の座標範囲をチェック
    assert 35.0 < first_result["latitude"] < 36.0
    assert 139.0 < first_result["longitude"] < 140.0

@pytest.mark.asyncio
async def test_geocode_empty_query():
    """空のクエリでのエラーハンドリングテスト"""
    result = await geocode(query="")
    
    assert "error" in result or result["count"] == 0
```

### 10.3 ライブテストスクリプト

**出典**: geo-base/mcp/tests/live_test.py

```python
#!/usr/bin/env python3
"""
ライブテストスクリプト

Usage:
    API_URL=http://localhost:3000 uv run python tests/live_test.py
"""

import asyncio
import os
from tools.tilesets import list_tilesets, get_tileset

async def main():
    print("=" * 60)
    print("🧪 Live Test Starting...")
    print("=" * 60)
    
    # Test 1: タイルセット一覧取得
    print("\n📋 Test 1: List Tilesets")
    result = await list_tilesets()
    print(f"   Tilesets found: {result.get('count', 0)}")
    
    # Test 2: 個別タイルセット取得
    if result.get("tilesets"):
        tileset_id = result["tilesets"][0]["id"]
        print(f"\n📍 Test 2: Get Tileset {tileset_id}")
        detail = await get_tileset(tileset_id)
        print(f"   Name: {detail.get('name')}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 11. エラーハンドリングベストプラクティス

### 11.1 カスタム例外クラス

```python
class MCPError(Exception):
    """MCP Server基底例外"""
    pass

class ValidationError(MCPError):
    """入力バリデーションエラー"""
    pass

class APIError(MCPError):
    """外部API呼び出しエラー"""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class AuthenticationError(MCPError):
    """認証エラー"""
    pass

class NotFoundError(MCPError):
    """リソースが見つからない"""
    pass
```

### 11.2 エラーレスポンスの標準化

```python
def handle_api_error(e: Exception) -> dict:
    """APIエラーを標準化されたレスポンスに変換"""
    if isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        if status_code == 401:
            return {"error": "認証が必要です", "code": "AUTH_REQUIRED"}
        elif status_code == 403:
            return {"error": "アクセス権限がありません", "code": "FORBIDDEN"}
        elif status_code == 404:
            return {"error": "リソースが見つかりません", "code": "NOT_FOUND"}
        elif status_code >= 500:
            return {"error": "サーバーエラーが発生しました", "code": "SERVER_ERROR"}
        else:
            return {"error": f"HTTPエラー: {status_code}", "code": "HTTP_ERROR"}
    
    elif isinstance(e, httpx.TimeoutException):
        return {"error": "リクエストがタイムアウトしました", "code": "TIMEOUT"}
    
    elif isinstance(e, httpx.NetworkError):
        return {"error": "ネットワークエラーが発生しました", "code": "NETWORK_ERROR"}
    
    else:
        return {"error": f"予期しないエラー: {str(e)}", "code": "UNKNOWN_ERROR"}
```

---

## 12. リトライ処理パターン

### 12.1 tenacityを使ったリトライ

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)
async def fetch_with_retry(url: str, params: dict | None = None) -> dict:
    """リトライ付きのAPI呼び出し"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

---

## 13. ロギングパターン

### 13.1 標準loggingの活用

```python
import logging
import os

def setup_logger(name: str) -> logging.Logger:
    """ロガーをセットアップ"""
    logger = logging.getLogger(name)
    
    # 環境変数からログレベルを取得
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # ハンドラーの設定
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# 使用例
logger = setup_logger("mcp-server")

async def my_tool(param: str) -> dict:
    logger.info(f"Tool called with param: {param}")
    try:
        result = await process(param)
        logger.debug(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing: {e}", exc_info=True)
        raise
```

---

## 14. バリデーションパターン

### 14.1 入力バリデーション関数

```python
import re
from typing import Tuple

def validate_uuid(value: str) -> Tuple[bool, str | None]:
    """UUIDフォーマットを検証"""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if uuid_pattern.match(value):
        return True, None
    return False, f"Invalid UUID format: {value}"

def validate_bbox(bbox: str) -> Tuple[bool, str | None]:
    """バウンディングボックスを検証"""
    try:
        parts = bbox.split(",")
        if len(parts) != 4:
            return False, "bbox must have 4 values: minx,miny,maxx,maxy"
        
        minx, miny, maxx, maxy = map(float, parts)
        
        if not (-180 <= minx <= 180 and -180 <= maxx <= 180):
            return False, "Longitude must be between -180 and 180"
        if not (-90 <= miny <= 90 and -90 <= maxy <= 90):
            return False, "Latitude must be between -90 and 90"
        if minx > maxx or miny > maxy:
            return False, "min values must be less than max values"
        
        return True, None
    except ValueError:
        return False, "bbox values must be numeric"

def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str | None]:
    """緯度経度を検証"""
    if not (-90 <= lat <= 90):
        return False, f"Latitude {lat} must be between -90 and 90"
    if not (-180 <= lon <= 180):
        return False, f"Longitude {lon} must be between -180 and 180"
    return True, None
```

---

## 15. まとめ：チェックリスト

### プロジェクト構成
- [ ] pyproject.tomlで依存関係を管理
- [ ] tools/ディレクトリで機能を分離
- [ ] tests/ディレクトリでテストを整理
- [ ] .env.exampleで必要な環境変数を文書化

### ツール実装
- [ ] 明確なdocstringを記述（Claudeに表示される）
- [ ] 入力バリデーションを実装
- [ ] 適切なエラーハンドリング
- [ ] 構造化されたレスポンス

### HTTP通信
- [ ] タイムアウトを設定
- [ ] HTTPステータスコード別のエラー処理
- [ ] 必要に応じてリトライ処理

### 品質
- [ ] pytest で単体テスト
- [ ] ruff でリント
- [ ] mypy で型チェック
- [ ] ロギングの実装

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2025-12-14 | 初版作成 |
