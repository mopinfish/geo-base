"""E2E テスト専用ヘルパー（環境変数 E2E_MODE=1 のときだけ登録される）。

Issue #110: Playwright から DB を冪等にリセットするための逃げ道。
本番には絶対に出してはいけない。

三重ガード:
1. lib.main で `E2E_MODE` が truthy でない限り include_router しない。
2. このモジュール内のハンドラでも `os.getenv("E2E_MODE") == "1"` を実行する。
3. ハンドラは `DATABASE_URL` の DB 名が `geo_base_e2e` で始まらないなら 400 で abort。
"""

import os
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

from lib.database import get_db_connection

router = APIRouter(prefix="/api/test", tags=["test-helpers"])


# DB 名チェックの prefix。ワーカー並列対応 (Phase 2) で `geo_base_e2e_w0` 等の
# サフィックスが付くケースを許容するため `startswith` で判定する。
_E2E_DB_PREFIX = "geo_base_e2e"


# Playwright からは下記テーブルを毎テストファイルの beforeAll で空にする想定。
# users と refresh_tokens は globalSetup で作った admin を保持するので touch しない。
# 注意: 「datasources」は API 上の概念で、実体は pmtiles_sources / raster_sources / tile_files
# の 3 テーブルに分かれている (api/lib/routers/datasources.py を参照)。
_RESETTABLE_TABLES = [
    # 依存順 (foreign key を考慮): 子から親へ
    "team_invitations",
    "team_members",
    "team_tilesets",
    "teams",
    "api_key_usage_logs",
    "api_key_rate_limits",
    "api_keys",
    "features",
    "pmtiles_sources",
    "raster_sources",
    "tile_files",
    "tilesets",
    "password_reset_tokens",
    "auth_login_attempts",
]


def _assert_e2e_mode_or_die() -> None:
    """ハンドラ突入時の二重防御。本番に出ても fail-closed にする。"""
    if os.getenv("E2E_MODE") != "1":
        raise HTTPException(status_code=404, detail="Not Found")


def _assert_e2e_database_or_die() -> None:
    """DATABASE_URL の DB 名が geo_base_e2e で始まらない場合は abort する。

    `geo_base` (dev) / `geo_base_test` (pytest) を誤って truncate するのを防ぐ。
    """
    db_url = os.getenv("DATABASE_URL", "")
    parsed = urlparse(db_url)
    db_name = (parsed.path or "").lstrip("/")
    if not db_name.startswith(_E2E_DB_PREFIX):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Refusing to reset: DATABASE_URL must point to a "
                f"{_E2E_DB_PREFIX}* database (got '{db_name}')"
            ),
        )


@router.post("/reset")
def reset_database():
    """主要テーブルを TRUNCATE する。users / refresh_tokens は保持する。"""
    _assert_e2e_mode_or_die()
    _assert_e2e_database_or_die()

    truncated = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for table in _RESETTABLE_TABLES:
                cur.execute(
                    f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"
                )
                truncated.append(table)
        conn.commit()
    return {"truncated": truncated}
