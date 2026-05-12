"""JWT エンコード・デコード。署名鍵・audience は引数指定。

このモジュールは純粋関数のみで、設定取得は呼び出し側の責任。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidSignatureError,
    InvalidTokenError,
)

from .errors import InvalidToken
from .models import User

ALGORITHM = "HS256"


def issue_access_token(
    user: User,
    *,
    secret: str,
    audience: str,
    issuer: str = "geo-base",
    ttl_seconds: int = 900,
) -> str:
    """HS256 で標準クレーム（sub/email/role/aud/iss/iat/exp）の JWT を発行する。"""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user.id,
        "aud": audience,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    if user.email is not None:
        payload["email"] = user.email
    if user.role is not None:
        payload["role"] = user.role
    if user.app_metadata is not None:
        payload["app_metadata"] = user.app_metadata
    if user.user_metadata is not None:
        payload["user_metadata"] = user.user_metadata

    return pyjwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, *, secret: str, audience: str) -> dict[str, Any]:
    """JWT を検証し、クレーム dict を返す。検証失敗時は InvalidToken を raise。"""
    try:
        return pyjwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=audience,
            options={"require": ["exp", "iat", "sub", "aud"]},
        )
    except ExpiredSignatureError:
        raise InvalidToken("Token has expired")
    except InvalidAudienceError:
        raise InvalidToken("Invalid token audience")
    except (InvalidSignatureError, DecodeError, InvalidAlgorithmError) as e:
        raise InvalidToken(f"Invalid token: {e}")
    except InvalidTokenError as e:
        raise InvalidToken(f"Invalid token: {e}")


def claims_to_user(claims: dict[str, Any]) -> User:
    """JWT クレーム dict を User モデルに変換。"""
    return User(
        id=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role"),
        app_metadata=claims.get("app_metadata"),
        user_metadata=claims.get("user_metadata"),
    )
