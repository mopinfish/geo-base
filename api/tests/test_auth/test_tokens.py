"""Tests for auth.tokens module - refresh token rotation + reuse detection."""
import uuid
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from lib._auth_pkg.tokens import (
    issue_refresh_token,
    verify_and_rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    cleanup_expired_tokens,
    REFRESH_TOKEN_TTL_DAYS,
)
from lib._auth_pkg.errors import InvalidToken


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


class TestIssueRefreshToken:
    def test_returns_string_token(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id, ip="127.0.0.1", user_agent="pytest")
        assert isinstance(token, str)
        assert len(token) > 32  # urlsafe(48) は ~64 文字

    def test_stored_as_hash(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT token_hash, user_id FROM refresh_tokens WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            assert row[0] == _hash(token)
            assert str(row[1]) == user_id

    def test_each_token_unique(self, db_conn, clean_auth_tables, user_id):
        t1 = issue_refresh_token(db_conn, user_id)
        t2 = issue_refresh_token(db_conn, user_id)
        assert t1 != t2


class TestVerifyAndRotate:
    def test_valid_rotation(self, db_conn, clean_auth_tables, user_id):
        original = issue_refresh_token(db_conn, user_id)
        returned_user_id, new_token = verify_and_rotate_refresh_token(db_conn, original)
        assert returned_user_id == user_id
        assert new_token != original
        # 旧トークンが revoked
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT revoked_at, replaced_by FROM refresh_tokens WHERE token_hash = %s",
                (_hash(original),),
            )
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] is not None

    def test_invalid_token_raises(self, db_conn, clean_auth_tables):
        with pytest.raises(InvalidToken):
            verify_and_rotate_refresh_token(db_conn, "nonexistent-token")

    def test_reuse_detection_revokes_all(self, db_conn, clean_auth_tables, user_id):
        # 2 つトークンを発行、1 つを使用→ローテート、その後旧トークンを再提示
        t1 = issue_refresh_token(db_conn, user_id)
        t2 = issue_refresh_token(db_conn, user_id)
        _, _ = verify_and_rotate_refresh_token(db_conn, t1)  # t1 は revoked になる
        # 再利用 → 全失効
        with pytest.raises(InvalidToken):
            verify_and_rotate_refresh_token(db_conn, t1)
        # t2 も revoked になっているはず
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT revoked_at, revoked_reason FROM refresh_tokens WHERE token_hash = %s",
                (_hash(t2),),
            )
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] == "theft_detected"

    def test_expired_token_raises(self, db_conn, clean_auth_tables, user_id):
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_refresh_token(db_conn, user_id)
        with freeze_time("2026-03-01 00:00:00"):  # 30 日以上経過
            with pytest.raises(InvalidToken):
                verify_and_rotate_refresh_token(db_conn, token)


class TestRevoke:
    def test_revoke_specific(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        revoke_refresh_token(db_conn, token, reason="logout")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT revoked_at, revoked_reason FROM refresh_tokens WHERE token_hash = %s",
                (_hash(token),),
            )
            row = cur.fetchone()
            assert row[0] is not None
            assert row[1] == "logout"

    def test_revoke_idempotent(self, db_conn, clean_auth_tables, user_id):
        token = issue_refresh_token(db_conn, user_id)
        revoke_refresh_token(db_conn, token)
        revoke_refresh_token(db_conn, token)  # 二重に呼んでも例外なし

    def test_revoke_nonexistent_no_error(self, db_conn, clean_auth_tables):
        revoke_refresh_token(db_conn, "nonexistent")  # 例外なし

    def test_revoke_all_user_tokens(self, db_conn, clean_auth_tables, user_id):
        for _ in range(3):
            issue_refresh_token(db_conn, user_id)
        count = revoke_all_user_tokens(db_conn, user_id, reason="password_changed")
        assert count == 3
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s AND revoked_at IS NOT NULL",
                (user_id,),
            )
            assert cur.fetchone()[0] == 3


class TestCleanup:
    def test_cleanup_expired(self, db_conn, clean_auth_tables, user_id):
        with freeze_time("2026-01-01 00:00:00"):
            issue_refresh_token(db_conn, user_id)
        with freeze_time("2026-04-01 00:00:00"):
            count = cleanup_expired_tokens(db_conn)
            assert count >= 1
