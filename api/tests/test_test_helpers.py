"""Tests for /api/test/reset and the E2E_MODE gate.

Issue #110: 本番には絶対に出ない E2E 用ルーター。

二重ガードを検証:
1. E2E_MODE が unset/falsy のときは main.py がルーターを include しない。
2. E2E_MODE=1 のときだけ POST /api/test/reset が動作する。
"""

import importlib

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
