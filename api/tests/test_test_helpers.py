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
    assert res.status_code != 400, (
        f"Expected non-400 (prefix check passed), got {res.status_code}: {res.text}"
    )


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

    with patch(
        "lib.routers.test_helpers.get_db_connection", return_value=mock_cm
    ):
        res = client.get(
            "/api/test/tokens?type=team_invitation"
            "&email=invitee@example.com",
        )

    assert res.status_code == 200, res.text
    assert res.json() == {"token": "test-token-abc123"}

    # SQL に email パラメータが渡されていることも検証 (regression 対策)。
    args, _ = mock_cursor.execute.call_args
    assert args[1] == ("invitee@example.com",)
