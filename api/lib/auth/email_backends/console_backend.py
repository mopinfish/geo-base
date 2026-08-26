"""ローカル開発用バックエンド。標準出力 + logger.info に出力。

Phase 3 (Issue #112): E2E_MODE 下で AUTH-08 (password reset confirm) を
テスト可能にするため、password reset URL に含まれる plain token を
email アドレスをキーにしたモジュール変数 dict に記録する。
本番では console backend が使われない前提 (email_backend=smtp) なので、
production には漏れない。
"""

import logging
import os
import re

from . import EmailBackend

logger = logging.getLogger(__name__)

# E2E_MODE で最新の password_reset token を email 別に保持する。
# test_helpers.GET /api/test/tokens?type=password_reset&email=... が読む。
_RECENT_PASSWORD_RESET_TOKENS: dict[str, str] = {}


def get_recent_password_reset_token(email: str) -> str | None:
    """E2E test_helpers から呼ばれる accessor。"""
    return _RECENT_PASSWORD_RESET_TOKENS.get(email.lower())


def _record_password_reset_token_if_present(email: str, body: str) -> None:
    """email 本文に `/password-reset/confirm?token=...` URL が含まれていたら
    token を抽出して dict に保持する。E2E_MODE=1 のときのみ動作。"""
    if os.getenv("E2E_MODE") != "1":
        return
    match = re.search(r"/password-reset/confirm\?token=([^\s\"&]+)", body)
    if not match:
        return
    token = match.group(1)
    # URL からそのまま取り出すので URL-decoded ではない値だが、token は
    # base64url-safe な文字 (`secrets.token_urlsafe(48)` 由来) なので URL
    # エンコードはされない前提。
    _RECENT_PASSWORD_RESET_TOKENS[email.lower()] = token


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
        # E2E_MODE 下で password reset URL の token を捕捉する。
        _record_password_reset_token_if_present(to, body)
