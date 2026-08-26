"""メール送信バックエンド。Null/Console/SMTP の 3 実装。"""

from abc import ABC, abstractmethod
from functools import lru_cache


class EmailBackend(ABC):
    """メール送信の抽象インタフェース。"""

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None:
        """プレーンテキストメールを送信する。"""


def _get_settings():
    """設定取得（遅延 import で循環依存を回避）"""
    from lib.config import get_settings

    return get_settings()


@lru_cache(maxsize=1)
def get_email_backend() -> EmailBackend:
    """環境変数 EMAIL_BACKEND から実装を選択。"""
    settings = _get_settings()
    backend_name = settings.email_backend

    if backend_name == "null":
        return NullEmailBackend()
    elif backend_name == "console":
        return ConsoleEmailBackend()
    elif backend_name == "smtp":
        return SMTPEmailBackend(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
            use_tls=settings.smtp_use_tls,
        )
    raise ValueError(f"Unknown EMAIL_BACKEND: {backend_name}")


# 実装を re-export
from .console_backend import ConsoleEmailBackend  # noqa: E402
from .null_backend import NullEmailBackend  # noqa: E402
from .smtp_backend import SMTPEmailBackend  # noqa: E402

__all__ = [
    "EmailBackend",
    "NullEmailBackend",
    "ConsoleEmailBackend",
    "SMTPEmailBackend",
    "get_email_backend",
]
