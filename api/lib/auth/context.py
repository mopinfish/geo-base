"""AuthContext - JWT ユーザーと API キーを統一的に扱うコンテキスト。"""
from typing import Optional
from pydantic import BaseModel

from .models import User


# スコープ階層（数値が大きいほど強い権限）
_SCOPE_HIERARCHY = {"read": 1, "write": 2, "delete": 3, "admin": 4}


class AuthContext(BaseModel):
    """JWT ユーザーと API キーの統一コンテキスト。"""

    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[str] = None  # API キーが特定のチームに紐付いている場合のみセット。
                                    # JWT ユーザーは常に None（所属チームは team_members を別途参照）
    scopes: list[str] = []
    is_api_key: bool = False
    api_key_id: Optional[str] = None

    @classmethod
    def from_jwt_user(cls, user: User) -> "AuthContext":
        """JWT 認証結果から作成。フルスコープを付与。"""
        return cls(
            user_id=user.id,
            email=user.email,
            role=user.role,
            scopes=["read", "write", "delete", "admin"],
            is_api_key=False,
        )

    @classmethod
    def from_api_key(cls, key_data: dict) -> "AuthContext":
        """API キー DB レコードから作成。"""
        return cls(
            user_id=str(key_data["user_id"]),
            team_id=str(key_data["team_id"]) if key_data.get("team_id") else None,
            scopes=list(key_data.get("scopes") or []),
            is_api_key=True,
            api_key_id=str(key_data["id"]),
        )

    def has_scope(self, required: str) -> bool:
        """admin > delete > write > read の階層で判定。"""
        if not self.scopes:
            return False
        required_level = _SCOPE_HIERARCHY.get(required, 0)
        max_level = max(_SCOPE_HIERARCHY.get(s, 0) for s in self.scopes)
        return max_level >= required_level
