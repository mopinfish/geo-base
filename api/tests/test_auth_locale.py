"""Tests for PATCH /api/auth/me/locale (i18n Phase 3 / Issue #107)."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _build_client(monkeypatch) -> tuple[TestClient, MagicMock]:
    """`require_auth` を override してテスト用ユーザーを返す + provider mock。

    戻り値は `(TestClient, provider_mock)`。`provider_mock` は `MagicMock` で、
    `update_preferred_locale` のみを `AsyncMock` として注入している
    (他属性は MagicMock の自動生成挙動)。
    """
    monkeypatch.setenv("E2E_MODE", "0")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )

    import lib.main as main_module

    importlib.reload(main_module)
    from lib.auth.models import User
    from lib.auth import require_auth

    fake_user = User(
        id="u-1",
        email="u@example.com",
        role="authenticated",
        name="Test",
        email_verified=True,
    )
    main_module.app.dependency_overrides[require_auth] = lambda: fake_user

    provider_mock = MagicMock()
    provider_mock.update_preferred_locale = AsyncMock(
        return_value=User(
            id="u-1",
            email="u@example.com",
            role="authenticated",
            name="Test",
            email_verified=True,
            preferred_locale="ja",
        )
    )

    return TestClient(main_module.app), provider_mock


def test_update_locale_accepts_ja(monkeypatch):
    client, provider_mock = _build_client(monkeypatch)
    with patch("lib.routers.auth.get_auth_provider", return_value=provider_mock):
        res = client.patch(
            "/api/auth/me/locale",
            json={"preferred_locale": "ja"},
        )
    assert res.status_code == 200, res.text
    assert res.json()["preferred_locale"] == "ja"
    provider_mock.update_preferred_locale.assert_awaited_once_with("u-1", "ja")


def test_update_locale_accepts_en(monkeypatch):
    client, provider_mock = _build_client(monkeypatch)
    provider_mock.update_preferred_locale.return_value.preferred_locale = "en"
    with patch("lib.routers.auth.get_auth_provider", return_value=provider_mock):
        res = client.patch(
            "/api/auth/me/locale",
            json={"preferred_locale": "en"},
        )
    assert res.status_code == 200, res.text
    provider_mock.update_preferred_locale.assert_awaited_once_with("u-1", "en")


def test_update_locale_accepts_null_to_clear(monkeypatch):
    """null を渡すと preferred_locale を NULL に戻せる (= cookie fallback)。"""
    client, provider_mock = _build_client(monkeypatch)
    provider_mock.update_preferred_locale.return_value.preferred_locale = None
    with patch("lib.routers.auth.get_auth_provider", return_value=provider_mock):
        res = client.patch(
            "/api/auth/me/locale",
            json={"preferred_locale": None},
        )
    assert res.status_code == 200, res.text
    provider_mock.update_preferred_locale.assert_awaited_once_with("u-1", None)


def test_update_locale_rejects_unsupported(monkeypatch):
    """en/ja/null 以外は 400 + envelope error code を返す。"""
    client, provider_mock = _build_client(monkeypatch)
    with patch("lib.routers.auth.get_auth_provider", return_value=provider_mock):
        res = client.patch(
            "/api/auth/me/locale",
            json={"preferred_locale": "fr"},
        )
    assert res.status_code == 400, res.text
    body = res.json()
    assert body["error"]["code"] == "validation_invalid_value"
    assert "preferred_locale" in body["error"]["details"]
    assert body["error"]["details"]["preferred_locale"] == "fr"
    provider_mock.update_preferred_locale.assert_not_awaited()


def test_update_locale_requires_auth(monkeypatch):
    """require_auth が override されていないとき (= 認証なし) は 401/403 で reject。

    本テストでは override 無しで Bearer なしでアクセスし、認証が要求される
    こと自体を確認する。
    """
    monkeypatch.setenv("E2E_MODE", "0")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/geo_base_e2e",
    )
    import lib.main as main_module
    importlib.reload(main_module)
    client = TestClient(main_module.app)
    res = client.patch(
        "/api/auth/me/locale",
        json={"preferred_locale": "ja"},
    )
    # require_auth は未認証なら 401 系を返す (実装に依存するため 401 or 403 を許容)
    assert res.status_code in {401, 403}, res.text
