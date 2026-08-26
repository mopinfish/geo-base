"""Tests for auth.errors module."""

import pytest

from lib.auth.errors import (
    AuthError,
    InvalidCredentials,
    InvalidToken,
    ProviderError,
    RateLimited,
    UserAlreadyExists,
    UserNotFound,
    WeakPassword,
)


class TestAuthErrorHierarchy:
    def test_all_subclass_auth_error(self):
        for cls in [
            InvalidCredentials,
            RateLimited,
            UserNotFound,
            UserAlreadyExists,
            InvalidToken,
            WeakPassword,
            ProviderError,
        ]:
            assert issubclass(cls, AuthError)
            assert issubclass(cls, Exception)

    def test_can_raise_with_message(self):
        with pytest.raises(InvalidCredentials, match="bad creds"):
            raise InvalidCredentials("bad creds")

    def test_can_catch_via_base_class(self):
        with pytest.raises(AuthError):
            raise RateLimited("locked out")
