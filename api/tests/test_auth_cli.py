"""Tests for `lib.auth.cli` non-interactive password handling.

Issue #110: globalSetup から `--password` で create-admin を呼べるようにする。
既存の `getpass` 経由の対話入力動作も維持されること。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_cmd_create_admin_uses_password_flag_when_provided():
    """`--password 'foo'` が渡されたとき getpass を呼ばずにそれを使う。"""
    from lib.auth import cli

    args = MagicMock()
    args.email = "e2e-admin@example.com"
    args.password = "E2E-pass-1!"
    args.name = "E2E Admin"

    mock_provider = MagicMock()
    mock_provider.create_user = AsyncMock(return_value=MagicMock(id="user-1", email=args.email))

    with patch("lib.auth.cli.get_auth_provider", return_value=mock_provider):
        with patch("lib.auth.cli.getpass.getpass") as mock_getpass:
            with patch("builtins.input") as mock_input:
                await cli.cmd_create_admin(args)

    mock_getpass.assert_not_called()
    mock_input.assert_not_called()
    mock_provider.create_user.assert_awaited_once()
    call_kwargs = mock_provider.create_user.await_args.kwargs
    assert call_kwargs["email"] == "e2e-admin@example.com"
    assert call_kwargs["password"] == "E2E-pass-1!"
    assert call_kwargs["name"] == "E2E Admin"


@pytest.mark.asyncio
async def test_cmd_create_admin_falls_back_to_getpass_when_password_flag_absent():
    """`--password` が None のときは従来どおり getpass で対話入力する。"""
    from lib.auth import cli

    args = MagicMock()
    args.email = "interactive@example.com"
    args.password = None
    args.name = None

    mock_provider = MagicMock()
    mock_provider.create_user = AsyncMock(return_value=MagicMock(id="u-2", email=args.email))

    with patch("lib.auth.cli.get_auth_provider", return_value=mock_provider):
        with patch("lib.auth.cli.getpass.getpass", side_effect=["pw", "pw"]) as mock_getpass:
            with patch("builtins.input", return_value=""):
                await cli.cmd_create_admin(args)

    assert mock_getpass.call_count == 2
    call_kwargs = mock_provider.create_user.await_args.kwargs
    assert call_kwargs["password"] == "pw"
