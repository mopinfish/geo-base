"""ローカル開発用バックエンド。標準出力 + logger.info に出力。"""
import logging
from . import EmailBackend


logger = logging.getLogger(__name__)


class ConsoleEmailBackend(EmailBackend):
    async def send(self, to: str, subject: str, body: str) -> None:
        message = (
            f"\n{'=' * 60}\n"
            f"📧 EMAIL (console backend)\n"
            f"{'-' * 60}\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"{'-' * 60}\n"
            f"{body}\n"
            f"{'=' * 60}\n"
        )
        print(message)
        logger.info("Email sent (console)", extra={"to": to, "subject": subject})
