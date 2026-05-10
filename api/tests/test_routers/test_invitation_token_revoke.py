"""Issue #55: 招待 token の受諾後失効化（再利用防止強化）の検証テスト。

I-2 防御層の確認:
- 受諾 / 失効 / キャンセル 時に `team_invitations.token` が NULL に書き換えられること
- NULL 化された旧 token を使った GET / POST が漏れなく拒否されること
- SQL 関数 `expire_old_invitations()` も同様に token を NULL にすること

ここでは「post-revocation の状態に置かれた招待」に対する HTTP レスポンスを
中心に検証する。受諾フロー全体（ユーザー作成 + 認証）のテストはスコープ外。
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.database import get_connection
from lib.routers.auth import router as auth_router


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------


class _CommitNoOpConn:
    """`db_conn` の薄い proxy。`commit()` を no-op にしてテスト分離を担保。

    handler 内の `conn.commit()` をテスト DB に流すと `db_conn.rollback()` で
    巻き戻せなくなるため、proxy で吸収する（test_write_api_key_auth.py と同パターン）。
    """

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def commit(self):
        pass


@pytest.fixture
def app(db_conn):
    """auth router を載せた最小 app。`get_connection` を db_conn に向ける。"""
    no_commit_conn = _CommitNoOpConn(db_conn)
    app = FastAPI()
    app.include_router(auth_router)

    def _get_conn():
        yield no_commit_conn

    app.dependency_overrides[get_connection] = _get_conn
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


@pytest.fixture
def make_invitation(db_conn):
    """招待行を直接 INSERT する factory。

    Returns: dict(id, team_id, email, token, status)
    """

    def _make(status="pending", token=None, expires_at=None, email=None):
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        if email is None:
            email = f"invitee-{uuid.uuid4().hex[:8]}@example.test"
        if token is None and status == "pending":
            token = uuid.uuid4().hex
        team_id = str(uuid.uuid4())
        owner_id = str(uuid.uuid4())
        slug = f"t{team_id[:8]}"

        with db_conn.cursor() as cur:
            # 最小構成: team を作って team_invitations を入れる
            cur.execute(
                "INSERT INTO teams (id, name, slug, owner_id) VALUES (%s, %s, %s, %s)",
                (team_id, slug, slug, owner_id),
            )
            cur.execute(
                """INSERT INTO team_invitations
                   (team_id, email, role, invited_by, token, status, expires_at)
                   VALUES (%s, %s, 'member', %s, %s, %s, %s)
                   RETURNING id""",
                (team_id, email, owner_id, token, status, expires_at),
            )
            inv_id = str(cur.fetchone()[0])

        return {
            "id": inv_id,
            "team_id": team_id,
            "email": email,
            "token": token,
            "status": status,
        }

    return _make


def _set_token_null(db_conn, inv_id, new_status):
    """受諾/失効/キャンセル後の DB 状態を再現するヘルパ。"""
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE team_invitations SET status = %s, token = NULL, accepted_at = NOW() WHERE id = %s",
            (new_status, inv_id),
        )


# ---------------------------------------------------------------------------
# GET /api/auth/invitations/{token}
# ---------------------------------------------------------------------------


class TestGetInvitationAfterRevoke:
    def test_pending_invitation_is_visible(self, client, make_invitation):
        """sanity: pending 状態の招待は GET で取得できる。"""
        inv = make_invitation()
        res = client.get(f"/api/auth/invitations/{inv['token']}")
        # has_existing_account 判定で auth provider にアクセスするため、
        # 200 (取得成功) または 500（provider 未設定など）になり得る。
        # ここでは「少なくとも 404 ではない」ことを確認する（pending は隠れていない）。
        assert res.status_code != 404, res.text

    def test_accepted_invitation_token_returns_404(
        self, client, make_invitation, db_conn
    ):
        """受諾後（status=accepted, token=NULL）の旧 token は 404。"""
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "accepted")

        res = client.get(f"/api/auth/invitations/{original_token}")
        assert res.status_code == 404, res.text

    def test_cancelled_invitation_token_returns_404(
        self, client, make_invitation, db_conn
    ):
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "cancelled")

        res = client.get(f"/api/auth/invitations/{original_token}")
        assert res.status_code == 404

    def test_expired_invitation_token_returns_404(
        self, client, make_invitation, db_conn
    ):
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "expired")

        res = client.get(f"/api/auth/invitations/{original_token}")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/auth/accept-invitation (replay attempt)
# ---------------------------------------------------------------------------


class TestAcceptInvitationReplayPrevention:
    def test_replay_after_accept_is_rejected(
        self, client, make_invitation, db_conn
    ):
        """受諾後に同じ旧 token で POST しても 400。"""
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "accepted")

        res = client.post(
            "/api/auth/accept-invitation",
            json={
                "token": original_token,
                "password": "NewPassword123!",
                "name": "Attacker",
            },
        )
        # 旧 token は DB から消えているので「Invalid invitation token」(400) で拒否
        assert res.status_code == 400, res.text

    def test_replay_after_cancel_is_rejected(
        self, client, make_invitation, db_conn
    ):
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "cancelled")

        res = client.post(
            "/api/auth/accept-invitation",
            json={
                "token": original_token,
                "password": "NewPassword123!",
                "name": "Attacker",
            },
        )
        assert res.status_code == 400

    def test_replay_after_expire_is_rejected(
        self, client, make_invitation, db_conn
    ):
        inv = make_invitation()
        original_token = inv["token"]
        _set_token_null(db_conn, inv["id"], "expired")

        res = client.post(
            "/api/auth/accept-invitation",
            json={
                "token": original_token,
                "password": "NewPassword123!",
                "name": "Attacker",
            },
        )
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# SQL function: expire_old_invitations()
# ---------------------------------------------------------------------------


class TestExpireOldInvitationsSql:
    def test_expire_old_invitations_clears_token(self, db_conn, make_invitation):
        """expire_old_invitations() は status=expired にすると同時に token=NULL する。"""
        # 期限切れの pending 招待を 1 つ作る
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        inv = make_invitation(expires_at=past)

        with db_conn.cursor() as cur:
            cur.execute("SELECT expire_old_invitations()")
            (count,) = cur.fetchone()
            assert count >= 1

            cur.execute(
                "SELECT status, token FROM team_invitations WHERE id = %s",
                (inv["id"],),
            )
            status, token = cur.fetchone()
        assert status == "expired"
        assert token is None, "expire_old_invitations() should NULL out the token"

    def test_expire_old_invitations_skips_non_pending(
        self, db_conn, make_invitation
    ):
        """すでに accepted な招待は触らない（既に token は NULL のはず）。"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        inv = make_invitation(status="accepted", token=None, expires_at=past)

        with db_conn.cursor() as cur:
            cur.execute("SELECT expire_old_invitations()")
            cur.fetchone()
            cur.execute(
                "SELECT status FROM team_invitations WHERE id = %s",
                (inv["id"],),
            )
            (status,) = cur.fetchone()
        assert status == "accepted", "expire should not touch non-pending rows"
