"""Tests for AuthProvider ABC and factory."""
import pytest
from lib._auth_pkg.provider import AuthProvider


class TestAuthProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AuthProvider()
