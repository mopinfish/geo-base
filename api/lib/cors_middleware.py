"""TwoTierCORSMiddleware - パス別に CORS ポリシーを切り替える。

/api/auth/* → strict（allow_origins 指定 + allow_credentials=true）
それ以外    → permissive（allow_origins=* + allow_credentials=false）
"""

from typing import Sequence

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

AUTH_PATH_PREFIX = "/api/auth/"


class TwoTierCORSMiddleware:
    """2 つの CORS 設定を path で切り替える ASGI ミドルウェア。"""

    def __init__(self, app: ASGIApp, strict_origins: Sequence[str]):
        self._strict = CORSMiddleware(
            app,
            allow_origins=list(strict_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._public = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._strict(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(AUTH_PATH_PREFIX):
            await self._strict(scope, receive, send)
        else:
            await self._public(scope, receive, send)
