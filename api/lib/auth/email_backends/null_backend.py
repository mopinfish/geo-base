"""テスト用バックエンド。送信せず内部リストに記録。"""
from . import EmailBackend


class NullEmailBackend(EmailBackend):
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})

    def clear(self) -> None:
        self.sent.clear()
