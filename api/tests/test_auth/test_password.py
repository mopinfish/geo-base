"""Tests for auth.password module."""
import pytest

from lib.auth.errors import WeakPassword
from lib.auth.password import (
    MIN_PASSWORD_LENGTH,
    check_password_policy,
    hash_password,
    verify_password,
)


class TestHashPassword:
    def test_returns_string(self):
        h = hash_password("ValidPass123")
        assert isinstance(h, str)
        assert len(h) > 50  # bcrypt ハッシュは 60 文字程度

    def test_different_calls_produce_different_hashes(self):
        # bcrypt は salt を含むため毎回違うハッシュになる
        h1 = hash_password("Same1234")
        h2 = hash_password("Same1234")
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password(self):
        h = hash_password("MyPass123")
        assert verify_password("MyPass123", h) is True

    def test_wrong_password(self):
        h = hash_password("MyPass123")
        assert verify_password("WrongPass", h) is False

    def test_invalid_hash_returns_false(self):
        # 不正なハッシュ文字列でも例外を出さず False を返す
        assert verify_password("anything", "not-a-bcrypt-hash") is False


class TestCheckPasswordPolicy:
    def test_valid_password(self):
        check_password_policy("ValidPass123")  # 例外なし

    def test_too_short(self):
        with pytest.raises(WeakPassword, match=str(MIN_PASSWORD_LENGTH)):
            check_password_policy("Short1")

    def test_letters_only(self):
        with pytest.raises(WeakPassword):
            check_password_policy("OnlyLetters")

    def test_digits_only(self):
        with pytest.raises(WeakPassword):
            check_password_policy("12345678")

    def test_letter_with_symbol_ok(self):
        check_password_policy("Hello!@#$")  # 英字 + 記号

    def test_letter_with_digit_ok(self):
        check_password_policy("Hello123")

    def test_no_max_length(self):
        # 最大長制限はない（NIST 推奨）
        check_password_policy("a" * 200 + "1")
