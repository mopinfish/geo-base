"""Issue #56 Phase 1: API キー rate limit backend 抽象化のテスト。

`api/lib/auth/api_key_rate_limit.py` の `DbRateLimiter` と `make_rate_limiter` を
ユニットレベルで検証する。`api_key_rate_limits` テーブル + SQL 関数
(`get_api_key_rate_limit_status` / `increment_api_key_rate_limit`) の挙動を
実 DB に対して確認する形。

Phase 2 で `RedisRateLimiter` を追加する際は本ファイルに parametrize して
両 backend を同じテストケースで cover する予定。
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from lib.auth.api_key_rate_limit import DbRateLimiter, make_rate_limiter
from lib.auth.errors import RateLimited


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_api_key(db_conn):
    """rate_limit_per_minute / per_day 指定で API キー row を作る factory。"""

    def _make(rl_min: int = 60, rl_day: int = 1000, user_id: str = None) -> str:
        key_id = str(uuid.uuid4())
        user_id = user_id or str(uuid.uuid4())
        # users テーブルに先に投入（FK 制約のため）
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO users (id, email, password_hash, role)
                   VALUES (%s, %s, 'x', 'user')
                   ON CONFLICT (id) DO NOTHING""",
                (user_id, f"u-{user_id[:8]}@example.test"),
            )
            cur.execute(
                """INSERT INTO api_keys (
                       id, user_id, key_hash, prefix, name,
                       rate_limit_per_minute, rate_limit_per_day,
                       is_active
                   )
                   VALUES (%s, %s, %s, 'gb_test_', 'test-key', %s, %s, true)""",
                (key_id, user_id, f"hash-{key_id[:8]}", rl_min, rl_day),
            )
        return key_id

    return _make


# ---------------------------------------------------------------------------
# DbRateLimiter: under-limit / over-limit / increment 挙動
# ---------------------------------------------------------------------------


class TestDbRateLimiter:
    def test_under_limit_does_not_raise(self, db_conn, make_api_key):
        key_id = make_api_key(rl_min=60, rl_day=1000)
        limiter = DbRateLimiter(db_conn)
        # 1 回目: カウント 0 → 60 未満なので raise しない
        limiter.check_and_increment(key_id, rl_min=60, rl_day=1000)

    def test_increment_persists(self, db_conn, make_api_key):
        """check_and_increment を 3 回呼ぶと counter が 3 になる。"""
        key_id = make_api_key(rl_min=60, rl_day=1000)
        limiter = DbRateLimiter(db_conn)
        for _ in range(3):
            limiter.check_and_increment(key_id, rl_min=60, rl_day=1000)
        with db_conn.cursor() as cur:
            cur.execute(
                """SELECT request_count FROM api_key_rate_limits
                   WHERE api_key_id = %s AND window_type = 'minute'""",
                (key_id,),
            )
            count = cur.fetchone()[0]
        assert count == 3

    def test_over_limit_raises(self, db_conn, make_api_key):
        """rate_limit_per_minute=2 にして 3 回目で RateLimited を raise する。"""
        key_id = make_api_key(rl_min=2, rl_day=1000)
        # api_key_rate_limits に直接 2 件カウントを投入して上限到達状態にする
        window_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_key_rate_limits
                       (api_key_id, window_type, window_start, request_count)
                   VALUES (%s, 'minute', %s, 2)""",
                (key_id, window_start),
            )

        limiter = DbRateLimiter(db_conn)
        with pytest.raises(RateLimited) as exc:
            limiter.check_and_increment(key_id, rl_min=2, rl_day=1000)
        assert "per minute" in str(exc.value)

    def test_check_then_raise_does_not_increment(self, db_conn, make_api_key):
        """raise した場合は counter は増えない（check が先、increment は後）。"""
        key_id = make_api_key(rl_min=1, rl_day=1000)
        window_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_key_rate_limits
                       (api_key_id, window_type, window_start, request_count)
                   VALUES (%s, 'minute', %s, 1)""",
                (key_id, window_start),
            )

        limiter = DbRateLimiter(db_conn)
        with pytest.raises(RateLimited):
            limiter.check_and_increment(key_id, rl_min=1, rl_day=1000)

        # counter は 1 のまま（increment されていない）
        with db_conn.cursor() as cur:
            cur.execute(
                """SELECT request_count FROM api_key_rate_limits
                   WHERE api_key_id = %s AND window_type = 'minute'
                     AND window_start = %s""",
                (key_id, window_start),
            )
            count = cur.fetchone()[0]
        assert count == 1

    def test_day_window_also_increments(self, db_conn, make_api_key):
        """per-day カウンタも同時に +1 される。"""
        key_id = make_api_key(rl_min=60, rl_day=1000)
        limiter = DbRateLimiter(db_conn)
        limiter.check_and_increment(key_id, rl_min=60, rl_day=1000)
        with db_conn.cursor() as cur:
            cur.execute(
                """SELECT request_count FROM api_key_rate_limits
                   WHERE api_key_id = %s AND window_type = 'day'""",
                (key_id,),
            )
            count = cur.fetchone()[0]
        assert count == 1


# ---------------------------------------------------------------------------
# make_rate_limiter factory
# ---------------------------------------------------------------------------


class TestMakeRateLimiter:
    def test_default_returns_db_rate_limiter(self, db_conn, monkeypatch):
        """既定 (`RATE_LIMIT_BACKEND` 未設定) は DbRateLimiter。"""
        monkeypatch.delenv("RATE_LIMIT_BACKEND", raising=False)
        from lib.config import get_settings
        get_settings.cache_clear()
        try:
            limiter = make_rate_limiter(db_conn)
            assert isinstance(limiter, DbRateLimiter)
        finally:
            get_settings.cache_clear()

    def test_explicit_db_backend(self, db_conn, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_BACKEND", "db")
        from lib.config import get_settings
        get_settings.cache_clear()
        try:
            limiter = make_rate_limiter(db_conn)
            assert isinstance(limiter, DbRateLimiter)
        finally:
            get_settings.cache_clear()

    def test_redis_backend_falls_back_to_db_in_phase1(
        self, db_conn, monkeypatch, caplog
    ):
        """Phase 1 では `RATE_LIMIT_BACKEND=redis` 指定でも DbRateLimiter
        にフォールバックし warn ログを出す。Phase 2 で RedisRateLimiter に
        切替予定。"""
        monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
        from lib.config import get_settings
        get_settings.cache_clear()
        try:
            import logging
            with caplog.at_level(logging.WARNING, logger="lib.auth.api_key_rate_limit"):
                limiter = make_rate_limiter(db_conn)
            assert isinstance(limiter, DbRateLimiter)
            assert any(
                "RedisRateLimiter is not yet implemented" in r.message
                for r in caplog.records
            )
        finally:
            get_settings.cache_clear()

    def test_unknown_backend_falls_back_to_db(self, db_conn, monkeypatch, caplog):
        monkeypatch.setenv("RATE_LIMIT_BACKEND", "memcached")
        from lib.config import get_settings
        get_settings.cache_clear()
        try:
            import logging
            with caplog.at_level(logging.WARNING, logger="lib.auth.api_key_rate_limit"):
                limiter = make_rate_limiter(db_conn)
            assert isinstance(limiter, DbRateLimiter)
            assert any(
                "Unknown RATE_LIMIT_BACKEND" in r.message for r in caplog.records
            )
        finally:
            get_settings.cache_clear()
