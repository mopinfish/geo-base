"""Tests for /api/test/reset and the E2E_MODE gate.

Issue #110: 本番には絶対に出ない E2E 用ルーター。

二重ガードを検証:
1. E2E_MODE が unset/falsy のときは main.py がルーターを include しない。
2. E2E_MODE=1 のときだけ POST /api/test/reset が動作する。
"""

import importlib
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _make_app(monkeypatch, e2e_mode: str | None):
    """`E2E_MODE` を変えた状態で `lib.main` を import し直して app を返す。"""
    if e2e_mode is None:
        monkeypatch.delenv("E2E_MODE", raising=False)
    else:
        monkeypatch.setenv("E2E_MODE", e2e_mode)

    # main の import 時にルーター登録判定が走るので、毎回 reload する
    import lib.main as main_module

    importlib.reload(main_module)
    return main_module.app


def test_reset_endpoint_is_404_when_e2e_mode_unset(monkeypatch):
    """E2E_MODE が unset なら /api/test/reset は 404。"""
    app = _make_app(monkeypatch, None)
    client = TestClient(app)
    res = client.post("/api/test/reset")
    assert res.status_code == 404


def test_reset_endpoint_is_404_when_e2e_mode_falsy(monkeypatch):
    """E2E_MODE=0 など truthy 以外でも 404。"""
    app = _make_app(monkeypatch, "0")
    client = TestClient(app)
    res = client.post("/api/test/reset")
    assert res.status_code == 404


def test_reset_endpoint_responds_when_e2e_mode_enabled(monkeypatch):
    """E2E_MODE=1 のとき /api/test/reset は 200 を返す。"""
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)
    res = client.post("/api/test/reset")
    # DB が geo_base_e2e でない場合は 400 で abort する想定
    # (後段の test と重複しない範囲で 200 or 400 のみ許容)
    assert res.status_code in (200, 400)


def test_reset_handler_aborts_on_wrong_database(monkeypatch):
    """DATABASE_URL の DB 名が geo_base_e2e で始まらないなら 400 で abort。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:15432/geo_base",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)
    res = client.post("/api/test/reset")
    assert res.status_code == 400
    assert "geo_base_e2e" in str(res.json())


def test_reset_handler_accepts_worker_database_prefix(monkeypatch):
    """`geo_base_e2e_w0` のような worker suffix も `startswith("geo_base_e2e")` で
    OK と判定される（Phase 2 worker 並列化のため）。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e_w0",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)
    res = client.post("/api/test/reset")
    # 接続できないなら 500 だが prefix チェックでは弾かれない（400 にならない）
    assert (
        res.status_code != 400
    ), f"Expected non-400 (prefix check passed), got {res.status_code}: {res.text}"


def test_tokens_endpoint_requires_email(monkeypatch):
    """email 未指定なら 400。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)
    res = client.get("/api/test/tokens?type=team_invitation")
    assert res.status_code == 400


def test_tokens_endpoint_404_when_e2e_mode_unset(monkeypatch):
    """E2E_MODE 未設定なら 404。"""
    app = _make_app(monkeypatch, None)
    client = TestClient(app)
    res = client.get(
        "/api/test/tokens?type=team_invitation&email=x@example.com",
    )
    assert res.status_code == 404


def test_tokens_endpoint_returns_pending_invitation_token(monkeypatch):
    """正常系: pending team_invitation の token が email で取得できる (200 + token)。

    実 DB を要求すると pytest 環境で flaky になるため、`get_db_connection` を
    mock で差し替えて SELECT が「token 文字列」を 1 行返す状態を作る。
    SQL の条件 (`status = 'pending'` AND `token IS NOT NULL`) や戻り値の形式が
    変わったらこのテストが落ちる。
    """
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)

    # cursor が SELECT 結果として ("test-token-abc123",) を返す mock を作る。
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("test-token-abc123",)
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=None)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=None)

    with patch("lib.routers.test_helpers.get_db_connection", return_value=mock_cm):
        res = client.get(
            "/api/test/tokens?type=team_invitation" "&email=invitee@example.com",
        )

    assert res.status_code == 200, res.text
    assert res.json() == {"token": "test-token-abc123"}

    # SQL に email パラメータが渡されていることも検証 (regression 対策)。
    args, _ = mock_cursor.execute.call_args
    assert args[1] == ("invitee@example.com",)


def test_tokens_endpoint_returns_password_reset_token_from_console_backend(
    monkeypatch,
):
    """console email backend が記録した password_reset token を取得できる。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    monkeypatch.setenv("E2E_MODE", "1")

    from lib.auth.email_backends import console_backend

    console_backend._RECENT_PASSWORD_RESET_TOKENS["admin@example.com"] = "test-reset-token-xyz"

    try:
        app = _make_app(monkeypatch, "1")
        client = TestClient(app)
        res = client.get("/api/test/tokens?type=password_reset&email=admin@example.com")
        assert res.status_code == 200, res.text
        assert res.json() == {"token": "test-reset-token-xyz"}
    finally:
        console_backend._RECENT_PASSWORD_RESET_TOKENS.pop("admin@example.com", None)


def test_tokens_endpoint_404_when_no_password_reset_token(monkeypatch):
    """password_reset token が dict に存在しないなら 404。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)

    from lib.auth.email_backends import console_backend

    # 念のため dict を空にする
    console_backend._RECENT_PASSWORD_RESET_TOKENS.pop("nobody@example.com", None)

    res = client.get("/api/test/tokens?type=password_reset&email=nobody@example.com")
    assert res.status_code == 404


def test_console_backend_records_password_reset_url_token(monkeypatch):
    """ConsoleEmailBackend.send 時に email 本文の URL から token を抽出する。"""
    import asyncio

    from lib.auth.email_backends.console_backend import (
        _RECENT_PASSWORD_RESET_TOKENS,
        ConsoleEmailBackend,
        get_recent_password_reset_token,
    )

    monkeypatch.setenv("E2E_MODE", "1")
    _RECENT_PASSWORD_RESET_TOKENS.clear()
    try:
        body = (
            "パスワードリセット URL:\n"
            "http://localhost:3000/password-reset/confirm?token=abc123xyz\n"
        )
        asyncio.run(ConsoleEmailBackend().send(to="user@example.com", subject="Reset", body=body))
        assert get_recent_password_reset_token("user@example.com") == "abc123xyz"
    finally:
        _RECENT_PASSWORD_RESET_TOKENS.clear()


def test_console_backend_does_not_record_when_e2e_mode_off(monkeypatch):
    """E2E_MODE が unset のときは token を記録しない (production 隔離)。"""
    import asyncio

    from lib.auth.email_backends.console_backend import (
        _RECENT_PASSWORD_RESET_TOKENS,
        ConsoleEmailBackend,
        get_recent_password_reset_token,
    )

    monkeypatch.delenv("E2E_MODE", raising=False)
    _RECENT_PASSWORD_RESET_TOKENS.clear()
    try:
        body = "http://localhost:3000/password-reset/confirm?token=should-not-record\n"
        asyncio.run(ConsoleEmailBackend().send(to="user2@example.com", subject="Reset", body=body))
        assert get_recent_password_reset_token("user2@example.com") is None
    finally:
        _RECENT_PASSWORD_RESET_TOKENS.clear()


def test_api_keys_expire_updates_existing_key(monkeypatch):
    """正常系: 既存 api_key の expires_at が過去日時に更新され 200 を返す
    (Copilot PR #122 指摘で追加)。

    DB を mock し、UPDATE の rowcount が 1 で commit() が呼ばれるパスを検証。
    """
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=None)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=None)

    with patch("lib.routers.test_helpers.get_db_connection", return_value=mock_cm):
        res = client.post(
            "/api/test/api-keys/expire",
            json={"key_id": "some-uuid", "minutes_ago": 60},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["key_id"] == "some-uuid"
    assert "expires_at" in body
    # UPDATE と commit() が確実に呼ばれていること。
    assert mock_cursor.execute.called
    assert mock_conn.commit.called


def test_api_keys_expire_returns_404_for_unknown_key(monkeypatch):
    """未知の key_id (rowcount=0) なら 404 を返し commit() しない
    (Copilot PR #122 指摘で追加)。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    app = _make_app(monkeypatch, "1")
    client = TestClient(app)

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 0
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=None)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=None)

    with patch("lib.routers.test_helpers.get_db_connection", return_value=mock_cm):
        res = client.post(
            "/api/test/api-keys/expire",
            json={"key_id": "nonexistent", "minutes_ago": 60},
        )

    assert res.status_code == 404, res.text
    # Phase 2b: envelope レスポンス `{error: {code, message, ...}}` に移行 (#106)
    body = res.json()
    assert "not found" in body["error"]["message"].lower()
    assert body["error"]["code"] == "api_key_not_found"
    # 失敗時に commit() を呼ばないこと。
    assert not mock_conn.commit.called
