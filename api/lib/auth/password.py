"""パスワードのハッシュ化・検証・ポリシーチェック。

bcrypt（passlib 経由）使用。NIST SP 800-63B 準拠で過度な複雑性は要求しない。
"""

from passlib.hash import bcrypt

from .errors import WeakPassword

MIN_PASSWORD_LENGTH = 8
BCRYPT_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    """bcrypt でパスワードをハッシュ化。salt は自動生成される。"""
    return bcrypt.using(rounds=BCRYPT_ROUNDS).hash(plaintext)


def verify_password(plaintext: str, hash_str: str) -> bool:
    """定時間比較でパスワードを検証。不正なハッシュ文字列でも例外を出さず False。"""
    try:
        return bcrypt.verify(plaintext, hash_str)
    except (ValueError, TypeError):
        return False


def check_password_policy(plaintext: str) -> None:
    """パスワードポリシー検証。違反時は WeakPassword を raise。

    ポリシー:
    - 最小 8 文字
    - 英字を 1 つ以上含む
    - 数字または記号を 1 つ以上含む
    """
    if len(plaintext) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    has_letter = any(c.isalpha() for c in plaintext)
    has_digit_or_symbol = any(c.isdigit() or not c.isalnum() for c in plaintext)

    if not has_letter:
        raise WeakPassword("Password must contain at least one letter")
    if not has_digit_or_symbol:
        raise WeakPassword("Password must contain at least one digit or symbol")
