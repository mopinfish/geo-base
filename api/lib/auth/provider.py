"""AuthProvider ABC - プラガブル認証の抽象インタフェース。"""

from abc import ABC, abstractmethod
from typing import Optional

from .models import AuthResult, TokenPair, User


class AuthProvider(ABC):
    """認証プロバイダの抽象インタフェース。

    起動時に AUTH_PROVIDER 環境変数で 1 つだけ生成される。
    実装: LocalAuthProvider
    （SupabaseAuthProvider は 2026-05-10 に削除済み — Issue #72）
    """

    # === トークン検証（毎リクエストで呼ばれる） ===
    @abstractmethod
    async def verify_access_token(self, token: str) -> AuthResult:
        """アクセストークンを検証する。"""

    # === ユーザー検索 ===
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID でユーザーを検索。存在しなければ None。"""

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """email でユーザーを検索。"""

    # === 認証フロー ===
    @abstractmethod
    async def authenticate(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """email/password でログインしトークンペアを返す。

        Raises:
            InvalidCredentials: 認証失敗
            RateLimited: 試行回数超過
        """

    @abstractmethod
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """リフレッシュトークンを使って新しいトークンペアを取得（rotation）。

        Raises:
            InvalidToken: 無効/期限切れ/revoked
        """

    @abstractmethod
    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """リフレッシュトークンを失効させる（ログアウト）。冪等。"""

    # === ユーザー作成・更新 ===
    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
        email_verified: bool = False,
        role: Optional[str] = None,
        app_metadata: Optional[dict] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        """新規ユーザーを作成。

        Args:
            role: `users.role` カラム値。None の場合はスキーマ default
                (`'authenticated'`) が適用される。`'admin'` を渡すと
                JWT payload にも `role: 'admin'` が乗る。

        Raises:
            UserAlreadyExists: email 重複
            WeakPassword: ポリシー違反
        """

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        """ユーザープロフィールを更新。

        Args:
            role: 指定時のみ `users.role` を上書き。既存 admin の修復や
                将来の昇格 / 降格用。公開 API 経由ではなく admin 限定
                operation で利用すること。
        """

    @abstractmethod
    async def update_password(self, user_id: str, new_password: str) -> None:
        """パスワードを更新。全 refresh token を失効させる責任は呼び出し側。"""

    # === パスワードリセット ===
    @abstractmethod
    async def request_password_reset(
        self,
        email: str,
        ip: Optional[str] = None,
    ) -> None:
        """パスワードリセットを要求（メール送信）。

        ユーザー存在の有無に関わらず常に成功する（情報漏洩防止）。
        """

    @abstractmethod
    async def confirm_password_reset(
        self,
        token: str,
        new_password: str,
    ) -> User:
        """リセットトークンで新パスワード設定。

        Raises:
            InvalidToken: トークン不正
            WeakPassword: ポリシー違反
        """

    @abstractmethod
    async def update_preferred_locale(
        self,
        user_id: str,
        preferred_locale: Optional[str],
    ) -> User:
        """ユーザーの UI locale を永続化 (i18n Phase 3 / Issue #107)。

        `preferred_locale=None` を渡すと `users.preferred_locale` を NULL に
        戻し、cookie / Accept-Language フォールバックに戻る。

        Raises:
            UserNotFound: 該当ユーザーが存在しない
        """
