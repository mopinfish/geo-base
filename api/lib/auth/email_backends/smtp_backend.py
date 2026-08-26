"""本番用 SMTP バックエンド。標準ライブラリのみ使用。"""

import smtplib
from email.message import EmailMessage
from typing import Optional

from . import EmailBackend


class SMTPEmailBackend(EmailBackend):
    def __init__(
        self,
        host: str,
        port: int,
        from_addr: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.from_addr = from_addr
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.set_content(body)

        # asyncio で同期 SMTP を呼ぶ（短時間処理なのでイベントループ blocking 許容）
        with smtplib.SMTP(self.host, self.port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)
