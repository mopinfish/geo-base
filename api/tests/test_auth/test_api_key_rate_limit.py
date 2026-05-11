"""Issue #56 Phase 1+2: API キー rate limit backend のテスト。

`api/lib/auth/api_key_rate_limit.py` の `DbRateLimiter` / `RedisRateLimiter` /
`make_rate_limiter` を実 backend (PostgreSQL / Redis) に対してユニットテスト。

Phase 1 (refactor): DbRateLimiter の挙動が旧 inline 実装と一致する確認。
Phase 2 (Redis): RedisRateLimiter の per-minute / per-day カウンタ + fail-open。
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from lib.auth.api_key_rate_limit import (
    DbRateLimiter,
    RedisRateLimiter,
    make_rate_limiter,
)
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

    def test_redis_backend_returns_redis_rate_limiter(self, db_conn, monkeypatch):
        """Phase 2: `RATE_LIMIT_BACKEND=redis` で RedisRateLimiter を返す。"""
        monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
        from lib.config import get_settings
        get_settings.cache_clear()
        try:
            limiter = make_rate_limiter(db_conn)
            assert isinstance(limiter, RedisRateLimiter)
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


# ---------------------------------------------------------------------------
# RedisRateLimiter (Phase 2)
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_limiter(monkeypatch):
    """テスト用 RedisRateLimiter。テスト前後で関連キーを掃除して分離する。

    docker-compose の redis (localhost:6379) に対して実通信する。Redis が
    起動していない CI 環境では skip（`get_redis()` が None を返すケースは
    fail-open のテスト側で別途 cover）。

    並行性テスト (TestConcurrency) では 100 並行 thread が同時に接続要求するため、
    既定の `REDIS_MAX_CONNECTIONS=10` ではプール枯渇で fail-open が誤発火する。
    本フィクスチャでテスト中だけ pool size を 200 に拡張し、singleton も
    リセットする。
    """
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "200")

    # singleton をリセットして新しい pool size で再作成させる
    import lib.redis_client as rc
    rc._redis_client = None
    rc._redis_available = None
    rc.get_redis_config.cache_clear()

    from lib.redis_client import get_redis

    client = get_redis()
    if client is None:
        pytest.skip("Redis is not available (docker-compose の redis を起動してください)")

    # 独自 prefix で他のテストやアプリケーションキャッシュと混ざらないようにする
    prefix = f"test:rate-limit:{uuid.uuid4().hex[:8]}"
    limiter = RedisRateLimiter(key_prefix=prefix)
    yield limiter

    # cleanup keys
    for key in client.scan_iter(f"{prefix}:*"):
        client.delete(key)

    # singleton を再度リセットして他のテストへの影響を絶つ
    rc._redis_client = None
    rc._redis_available = None
    rc.get_redis_config.cache_clear()


class TestRedisRateLimiter:
    def test_under_limit_does_not_raise(self, redis_limiter):
        key_id = str(uuid.uuid4())
        # 制限 5/min 内なら raise しない
        for _ in range(5):
            redis_limiter.check_and_increment(key_id, rl_min=5, rl_day=1000)

    def test_over_per_minute_raises(self, redis_limiter):
        key_id = str(uuid.uuid4())
        # 制限 3/min を 4 回目で超過
        for _ in range(3):
            redis_limiter.check_and_increment(key_id, rl_min=3, rl_day=1000)
        with pytest.raises(RateLimited) as exc:
            redis_limiter.check_and_increment(key_id, rl_min=3, rl_day=1000)
        assert "per minute" in str(exc.value)

    def test_over_per_day_raises(self, redis_limiter):
        """per-minute 余裕、per-day だけ超過のシナリオ。"""
        key_id = str(uuid.uuid4())
        # 制限 100/min, 2/day。3 回目で per-day 超過
        for _ in range(2):
            redis_limiter.check_and_increment(key_id, rl_min=100, rl_day=2)
        with pytest.raises(RateLimited) as exc:
            redis_limiter.check_and_increment(key_id, rl_min=100, rl_day=2)
        assert "per day" in str(exc.value)

    def test_separate_keys_are_independent(self, redis_limiter):
        """異なる api_key_id のカウンタは干渉しない。"""
        key_a = str(uuid.uuid4())
        key_b = str(uuid.uuid4())
        for _ in range(2):
            redis_limiter.check_and_increment(key_a, rl_min=2, rl_day=1000)
        # A は上限到達でも B は影響なし
        with pytest.raises(RateLimited):
            redis_limiter.check_and_increment(key_a, rl_min=2, rl_day=1000)
        redis_limiter.check_and_increment(key_b, rl_min=2, rl_day=1000)

    def test_window_boundary_resets_counter(self, redis_limiter):
        """次の minute 窓に切り替わるとカウンタがリセットされる。

        実際に 60 秒待つのではなく、`_now()` をパッチして窓境界を跨ぐシミュレーション。
        """
        key_id = str(uuid.uuid4())
        t0 = datetime(2026, 5, 11, 12, 30, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 5, 11, 12, 31, 0, tzinfo=timezone.utc)

        with patch.object(redis_limiter, "_now", return_value=t0):
            for _ in range(3):
                redis_limiter.check_and_increment(key_id, rl_min=3, rl_day=1000)
            # 窓内 3 件目を超えると raise
            with pytest.raises(RateLimited):
                redis_limiter.check_and_increment(key_id, rl_min=3, rl_day=1000)

        # 次の窓では再度 3 件まで通過
        with patch.object(redis_limiter, "_now", return_value=t1):
            for _ in range(3):
                redis_limiter.check_and_increment(key_id, rl_min=3, rl_day=1000)

    def test_fail_open_when_redis_unavailable(self, monkeypatch, caplog):
        """`get_redis()` が None を返した場合、raise せず warn ログのみ。"""
        import logging
        # `RedisRateLimiter.check_and_increment` 内の `from lib.redis_client import get_redis`
        # を None 返却にパッチ
        monkeypatch.setattr("lib.redis_client.get_redis", lambda: None)
        limiter = RedisRateLimiter()
        with caplog.at_level(logging.WARNING, logger="lib.auth.api_key_rate_limit"):
            limiter.check_and_increment(str(uuid.uuid4()), rl_min=5, rl_day=1000)
        assert any("fail-open" in r.message for r in caplog.records)

    def test_fail_open_when_redis_raises(self, monkeypatch, caplog):
        """Redis コマンドが例外を投げた場合も fail-open。"""
        import logging

        class _BrokenClient:
            def incr(self, key):
                raise RuntimeError("connection reset by peer")

        monkeypatch.setattr("lib.redis_client.get_redis", lambda: _BrokenClient())
        limiter = RedisRateLimiter()
        with caplog.at_level(logging.WARNING, logger="lib.auth.api_key_rate_limit"):
            limiter.check_and_increment(str(uuid.uuid4()), rl_min=5, rl_day=1000)
        assert any(
            "Redis rate limit operation failed" in r.message for r in caplog.records
        )

    @pytest.mark.parametrize("limit_value", [None, 0, -1])
    def test_unlimited_skips_check(self, redis_limiter, limit_value):
        """rl_min が None / 0 / 負値 (= 無制限) なら何回呼んでも raise しない。"""
        key_id = str(uuid.uuid4())
        # rl_day も無制限にして per-day 経路も skip
        for _ in range(20):
            redis_limiter.check_and_increment(
                key_id, rl_min=limit_value, rl_day=limit_value
            )

    def test_default_prefix_includes_global_redis_prefix(self):
        """key_prefix 未指定時は REDIS_KEY_PREFIX (既定 `geo-base:`) を含む。"""
        from lib.redis_client import get_redis_config

        # singleton reset せずに既存 config を使うが、本テストは prefix 文字列の
        # 組み立てを検証するだけなので Redis への接続は不要
        expected_global = get_redis_config().key_prefix  # "geo-base:" by default
        limiter = RedisRateLimiter()
        assert limiter._key_prefix.startswith(expected_global), (
            f"Expected key_prefix to start with {expected_global!r}, "
            f"got {limiter._key_prefix!r}"
        )
        assert limiter._key_prefix.endswith("rate:apikey"), (
            f"Expected key_prefix to end with 'rate:apikey', "
            f"got {limiter._key_prefix!r}"
        )

    def test_expire_set_on_first_increment(self, redis_limiter):
        """新規キー作成時のみ EXPIRE が設定される（INCR 戻り値 == 1）。"""
        from lib.redis_client import get_redis

        client = get_redis()
        key_id = str(uuid.uuid4())

        # `_now()` を固定時刻にパッチして、limiter が使うキーとアサート時のキーが
        # 分境界をまたいで乖離しないようにする (旧実装は分境界付近で flaky だった)。
        fixed_now = datetime(2026, 5, 11, 12, 30, 0, tzinfo=timezone.utc)
        minute_window = int(fixed_now.timestamp() // 60)
        minute_key = f"{redis_limiter._key_prefix}:{key_id}:m:{minute_window}"

        with patch.object(redis_limiter, "_now", return_value=fixed_now):
            redis_limiter.check_and_increment(key_id, rl_min=10, rl_day=1000)
            ttl = client.ttl(minute_key)

        # TTL は 120 秒以下で正の値（ちょうど 120 とは限らないため >= 100 で確認）
        assert 100 < ttl <= 120, f"Expected TTL ~120s, got {ttl}"

    def test_ttl_self_recovers_for_orphan_key(self, redis_limiter):
        """過去の EXPIRE 失敗で TTL 未設定 (-1) のキーが残った場合、次の
        check_and_increment で TTL が自己回復する (EXPIRE NX の効果)。"""
        from lib.redis_client import get_redis

        client = get_redis()
        key_id = str(uuid.uuid4())
        fixed_now = datetime(2026, 5, 11, 12, 30, 0, tzinfo=timezone.utc)
        minute_window = int(fixed_now.timestamp() // 60)
        minute_key = f"{redis_limiter._key_prefix}:{key_id}:m:{minute_window}"

        # 「INCR は成功したが EXPIRE が失敗した」状態を再現:
        # INCR 直接実行 → TTL を意図的に PERSIST (-1) にする
        client.incr(minute_key)
        client.persist(minute_key)
        assert client.ttl(minute_key) == -1, "Test setup: key must have no TTL"

        # 次の check_and_increment で TTL が付与されることを期待
        with patch.object(redis_limiter, "_now", return_value=fixed_now):
            redis_limiter.check_and_increment(key_id, rl_min=100, rl_day=10000)
            ttl = client.ttl(minute_key)

        assert 100 < ttl <= 120, (
            f"Expected TTL to be self-recovered to ~120s, got {ttl}. "
            "EXPIRE NX should set TTL on previously-orphan key."
        )

    def test_existing_ttl_not_extended(self, redis_limiter):
        """EXPIRE NX なので、既に TTL があるキーには TTL を再延長しない
        （窓のリセットタイミングが意図せず後ろにずれるのを防ぐ）。"""
        from lib.redis_client import get_redis

        client = get_redis()
        key_id = str(uuid.uuid4())
        fixed_now = datetime(2026, 5, 11, 12, 30, 0, tzinfo=timezone.utc)
        minute_window = int(fixed_now.timestamp() // 60)
        minute_key = f"{redis_limiter._key_prefix}:{key_id}:m:{minute_window}"

        # 1 回目: TTL が付与される
        with patch.object(redis_limiter, "_now", return_value=fixed_now):
            redis_limiter.check_and_increment(key_id, rl_min=100, rl_day=10000)

        # 手動で TTL を短くする (60s に削る)
        client.expire(minute_key, 60)
        first_modified_ttl = client.ttl(minute_key)
        assert first_modified_ttl <= 60

        # 2 回目: NX なので TTL は再延長されない（60s 以下のまま）
        with patch.object(redis_limiter, "_now", return_value=fixed_now):
            redis_limiter.check_and_increment(key_id, rl_min=100, rl_day=10000)
            second_ttl = client.ttl(minute_key)

        assert second_ttl <= 60, (
            f"Expected TTL not to be extended (was 60, got {second_ttl}). "
            "EXPIRE NX must not overwrite existing TTL."
        )


# ---------------------------------------------------------------------------
# Concurrency (Phase 3) — 100 並行リクエストで Redis backend が正確に counter を
# 管理することを確認。Issue #56 受け入れ基準「100 並行リクエスト時に DB 同期実装
# より明確にスループット改善」のうち、Redis 側の正当性を deterministic に検証する。
#
# DB backend の並行性ベンチは contention で遅くなるが、_CommitNoOpConn を使う
# テストでは real commit が走らないため正確な並行比較ができない。Issue 受け入れ
# 基準の「ベンチ取得」はマージ後にステージング/本番で wrk / ab 等で別途取得する想定
# （PR description に手順を記載）。
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_redis_100_concurrent_under_limit(self, redis_limiter):
        """rl_min=100 で 100 並行リクエストが全て通過し、101 件目が拒否される。"""
        import asyncio

        key_id = str(uuid.uuid4())

        async def call() -> bool:
            try:
                await asyncio.to_thread(
                    redis_limiter.check_and_increment,
                    key_id,
                    100,  # rl_min
                    10000,  # rl_day
                )
                return True
            except RateLimited:
                return False

        # 100 並行
        results = await asyncio.gather(*[call() for _ in range(100)])
        assert all(results), "All 100 requests within limit should pass"
        assert sum(results) == 100

        # 101 件目
        result = await call()
        assert result is False, "101st request should be rejected"

    @pytest.mark.asyncio
    async def test_redis_concurrent_over_limit_count_is_accurate(self, redis_limiter):
        """rl_min=50 で 100 並行 → 正確に 50 通過 / 50 拒否。

        INCR は atomic なので、並行下でも counter は 100 になり、戻り値で
        50 件目までが pass、51-100 件目が rate limited で reject される。
        """
        import asyncio

        key_id = str(uuid.uuid4())

        async def call() -> bool:
            try:
                await asyncio.to_thread(
                    redis_limiter.check_and_increment,
                    key_id,
                    50,  # rl_min
                    10000,  # rl_day
                )
                return True
            except RateLimited:
                return False

        results = await asyncio.gather(*[call() for _ in range(100)])
        passed = sum(results)
        # ちょうど 50 通過 (INCR atomic なので race condition はない)
        assert passed == 50, f"Expected exactly 50 to pass, got {passed}"
