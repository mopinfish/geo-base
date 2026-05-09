"""認証関連エラー階層。すべて AuthError を継承する。"""


class AuthError(Exception):
    """認証エラーの基底クラス。"""


class InvalidCredentials(AuthError):
    """email/password 不一致、または検証不可能なトークン。"""


class RateLimited(AuthError):
    """ログイン失敗回数が閾値を超過。"""


class UserNotFound(AuthError):
    """指定されたユーザーが存在しない。"""


class UserAlreadyExists(AuthError):
    """既に同じ email でアカウントが存在する。"""


class InvalidToken(AuthError):
    """JWT/refresh/reset トークンが無効・期限切れ・revoked。"""


class WeakPassword(AuthError):
    """パスワードがポリシーを満たさない。"""


class ProviderError(AuthError):
    """上流プロバイダ（Supabase API 等）のエラー。"""
