"""Tests for auth.rate_limit module."""

import pytest

from lib.auth.errors import RateLimited
from lib.auth.rate_limit import (
    MAX_FAILED_ATTEMPTS,
    check_login_rate_limit,
    cleanup_old_attempts,
    record_login_attempt,
)


class TestCheckLoginRateLimit:
    def test_no_attempts_passes(self, db_conn, clean_auth_tables):
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_under_threshold_passes(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            record_login_attempt(db_conn, email="x@example.com", success=False, ip="1.1.1.1")
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_at_threshold_raises(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email="x@example.com", success=False, ip="1.1.1.1")
        with pytest.raises(RateLimited):
            check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_success_does_not_count(self, db_conn, clean_auth_tables):
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email="x@example.com", success=True, ip="1.1.1.1")
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_old_attempts_ignored(self, db_conn, clean_auth_tables):
        # Insert old attempts directly via DB (freezegun + PG NOW() doesn't work)
        for _ in range(MAX_FAILED_ATTEMPTS):
            with db_conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO auth_login_attempts (email, ip_address, success, attempted_at)
                       VALUES (%s, %s, FALSE, NOW() - INTERVAL '1 hour')""",
                    ("x@example.com", "1.1.1.1"),
                )
        db_conn.commit()
        # Should NOT raise (attempts are 1 hour old, beyond 15-minute window)
        check_login_rate_limit(db_conn, email="x@example.com", ip="1.1.1.1")

    def test_ip_threshold_independently_triggers(self, db_conn, clean_auth_tables):
        # 別 email でも同じ IP から失敗を重ねるとロック
        for i in range(MAX_FAILED_ATTEMPTS):
            record_login_attempt(db_conn, email=f"user{i}@example.com", success=False, ip="1.1.1.1")
        with pytest.raises(RateLimited):
            check_login_rate_limit(db_conn, email="newuser@example.com", ip="1.1.1.1")


class TestRecordLoginAttempt:
    def test_records_email_lowercased(self, db_conn, clean_auth_tables):
        record_login_attempt(db_conn, email="UPPER@example.com", success=True, ip="1.1.1.1")
        with db_conn.cursor() as cur:
            cur.execute("SELECT email FROM auth_login_attempts")
            assert cur.fetchone()[0] == "upper@example.com"

    def test_includes_user_agent(self, db_conn, clean_auth_tables):
        record_login_attempt(
            db_conn, email="x@y.com", success=False, ip="1.1.1.1", user_agent="pytest/1.0"
        )
        with db_conn.cursor() as cur:
            cur.execute("SELECT user_agent FROM auth_login_attempts")
            assert cur.fetchone()[0] == "pytest/1.0"


class TestCleanup:
    def test_cleanup_old(self, db_conn, clean_auth_tables):
        # Insert old attempt directly
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO auth_login_attempts (email, ip_address, success, attempted_at)
                   VALUES (%s, %s, FALSE, NOW() - INTERVAL '2 days')""",
                ("x@y.com", "1.1.1.1"),
            )
        db_conn.commit()
        count = cleanup_old_attempts(db_conn)
        assert count >= 1
