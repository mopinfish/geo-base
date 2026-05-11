"""共通モデル定義。プロバイダ非依存。"""
from typing import Any, Optional

from pydantic import BaseModel


class User(BaseModel):
    """認証済みユーザーモデル。"""
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    app_metadata: Optional[dict[str, Any]] = None
    user_metadata: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    email_verified: bool = False
    # i18n Phase 3 (#107): Admin UI が言語切替時に PATCH /api/auth/me/locale
    # で更新する。null = 未設定 (cookie / Accept-Language フォールバック)。
    preferred_locale: Optional[str] = None


class AuthResult(BaseModel):
    """JWT 検証結果。"""
    is_authenticated: bool
    user: Optional[User] = None
    error: Optional[str] = None


class TokenPair(BaseModel):
    """ログイン/リフレッシュ時のトークンレスポンス。"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
