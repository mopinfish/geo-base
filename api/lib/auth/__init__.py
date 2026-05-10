"""auth パッケージ。

公開シンボル:
- User, AuthResult, TokenPair: モデル
- AuthError 系: エラー階層
- AuthProvider: 抽象インタフェース
- get_auth_provider(): factory
- require_auth, get_current_user: FastAPI dependencies (既存互換)
- verify_jwt_token: 後方互換用エイリアス
- extract_token_from_header: 既存ヘルパ
- is_auth_configured: 認証設定チェック
- check_tileset_access_v2: タイルセット読み取り認可（ctx ベース）
- check_tileset_write_access_v2: タイルセット書き込み認可（ctx ベース、issue #49）
"""
from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Header, HTTPException, status

from .api_key_auth import API_KEY_PREFIX, log_api_key_request, validate_api_key
from .context import AuthContext
from .errors import (
    AuthError,
    InvalidCredentials,
    InvalidToken,
    ProviderError,
    RateLimited,
    UserAlreadyExists,
    UserNotFound,
    WeakPassword,
)
from .models import AuthResult, TokenPair, User
from .provider import AuthProvider


@lru_cache(maxsize=1)
def get_auth_provider() -> AuthProvider:
    """環境変数 AUTH_PROVIDER からプロバイダを選択。"""
    from lib.config import get_settings
    settings = get_settings()

    if settings.auth_provider == "local":
        from .providers.local import LocalAuthProvider
        return LocalAuthProvider()
    elif settings.auth_provider == "supabase":
        from .providers.supabase import SupabaseAuthProvider
        return SupabaseAuthProvider()

    raise ValueError(f"Unknown AUTH_PROVIDER: {settings.auth_provider}")


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """Authorization ヘッダから 'Bearer xxx' の xxx を取り出す。"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1]


# === 後方互換エイリアス ===
def verify_jwt_token(token: str) -> AuthResult:
    """既存コード互換。新規コードは get_auth_provider().verify_access_token() を使うこと。"""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        get_auth_provider().verify_access_token(token)
    )


# === FastAPI Dependencies ===

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[User]:
    """認証済みユーザーを返す。未認証なら None（例外なし）。"""
    if not authorization:
        return None
    token = extract_token_from_header(authorization)
    if not token:
        return None

    result = await get_auth_provider().verify_access_token(token)
    if result.is_authenticated and result.user:
        return result.user
    return None


async def require_auth(
    authorization: Annotated[Optional[str], Header()] = None,
) -> User:
    """認証必須。失敗時 401。"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await get_auth_provider().verify_access_token(token)
    if not result.is_authenticated or not result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result.user


# 旧 `check_tileset_access` / `get_tileset_with_access_check` は team_tilesets
# 共有を考慮できなかったため、issue #51（ACCESS_CONTROL_REVIEW C-3）で削除。
# 認可判定は `check_tileset_access_v2(conn, tileset, ctx)` に統一されている。


def is_auth_configured() -> bool:
    """認証が正しく設定されているかチェック（後方互換）。"""
    from lib.config import get_settings
    return bool(get_settings().effective_jwt_secret)


# === Unified Auth Dependencies (Task 3.2) ===

async def get_auth_context_optional(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[AuthContext]:
    """JWT または API キーで認証。未認証なら None。"""
    if not authorization:
        return None
    token = extract_token_from_header(authorization)
    if not token:
        return None

    # API キー判別
    if token.startswith(API_KEY_PREFIX):
        try:
            return await validate_api_key(token)
        except RateLimited:
            raise HTTPException(429, "API key rate limit exceeded")

    # JWT パス
    result = await get_auth_provider().verify_access_token(token)
    if result.is_authenticated and result.user:
        return AuthContext.from_jwt_user(result.user)
    return None


async def require_auth_context(
    authorization: Annotated[Optional[str], Header()] = None,
) -> AuthContext:
    """JWT または API キーで認証必須。"""
    ctx = await get_auth_context_optional(authorization)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


async def check_tileset_access_v2(conn, tileset: dict, ctx: Optional["AuthContext"]) -> bool:
    """タイルセットアクセス判定。

    ルール:
    1. 公開タイルセット → 誰でも可
    2. 認証なし → 不可
    3. read スコープなし → 不可
    4. オーナー → 可
    5. API キー（チーム紐付け）+ team_tilesets で共有 → 可
    6. JWT ユーザー + 所属チーム経由で共有 → 可
    """
    import asyncio

    if tileset.get("is_public"):
        return True
    if ctx is None:
        return False
    if not ctx.has_scope("read"):
        return False

    owner_id = tileset.get("user_id")
    if owner_id and ctx.user_id == str(owner_id):
        return True

    tileset_id = str(tileset["id"])

    if ctx.is_api_key:
        if ctx.team_id is None:
            return False
        return await asyncio.to_thread(_is_tileset_shared_with_team, conn, tileset_id, ctx.team_id)

    # JWT ユーザー: 所属する全チームを横断
    return await asyncio.to_thread(_user_has_team_access, conn, ctx.user_id, tileset_id)


def _is_tileset_shared_with_team(conn, tileset_id: str, team_id: str) -> bool:
    import psycopg2
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM team_tilesets WHERE team_id = %s AND tileset_id = %s LIMIT 1",
                (team_id, tileset_id),
            )
            return cur.fetchone() is not None
    except psycopg2.errors.InvalidTextRepresentation:
        # team_id / tileset_id が UUID 形式でない場合 → アクセス不可
        conn.rollback()
        return False


def _user_has_team_access(conn, user_id: str, tileset_id: str) -> bool:
    import psycopg2
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM team_members tm
                   JOIN team_tilesets tt ON tm.team_id = tt.team_id
                  WHERE tm.user_id = %s AND tt.tileset_id = %s
                  LIMIT 1""",
                (user_id, tileset_id),
            )
            return cur.fetchone() is not None
    except psycopg2.errors.InvalidTextRepresentation:
        # user_id / tileset_id が UUID 形式でない場合 → アクセス不可
        conn.rollback()
        return False


# ============================================================================
# Write access (issue #49 / ACCESS_CONTROL_REVIEW C-1)
# ============================================================================
#
# update / delete などの書き込み系操作は、個人タイルセットの所有者だけでなく、
# `team_tilesets` 経由で共有されたタイルセットに対する team_member も
# permission_level に応じて許可する必要がある。判定ロジックは DB 側の
# `can_user_perform_action()` SQL 関数に集約済み（docker/postgis-init/
# 05_teams_schema.sql L195-217）なので、JWT ユーザー経路ではそれに委譲する。
# API キー経路は team_id ベースで team_tilesets.permission_level を直接見る。

# 書き込み action 名 → 必要な scope。`check_tileset_write_access_v2` は
# 書き込み（create / update / delete）専用ヘルパなので、ここに `read` は
# 含めない（読み取りは `check_tileset_access_v2` を使うこと）。
# 未登録の action は禁止する（タイポ等で許可判定が誤って通らないよう、
# `check_tileset_write_access_v2` 入口で明示的に弾く）。
_ACTION_REQUIRED_SCOPE = {
    "create": "write",
    "update": "write",
    "delete": "delete",
}


async def check_tileset_write_access_v2(
    conn,
    tileset: dict,
    ctx: Optional["AuthContext"],
    required_action: str,
) -> bool:
    """タイルセット書き込み認可判定（create / update / delete 専用）。

    読み取り認可は `check_tileset_access_v2` を使うこと。

    ルール:
    1. 認証なし → 不可
    2. `required_action` が `_ACTION_REQUIRED_SCOPE` に未登録 → 不可
       （タイポ / 未対応 action を即拒否）
    3. 必要な scope が不足 → 不可（API キー想定）
    4. 個人タイルセット所有者（tileset.user_id == ctx.user_id）→ 常に可
    5. JWT ユーザー: `can_user_perform_action(user_id, tileset_id, action)`
       SQL 関数で team_member.role と team_tilesets.permission_level を
       考慮した判定を行う
    6. API キー: ctx.team_id が共有先 team の場合のみ、team_tilesets の
       permission_level が action に対して十分か判定（team_role の継承は
       適用しない — API キーは team の "代理" だが特定 user の権限を継承
       しないため）

    Args:
        required_action: `"create"`、`"update"`、`"delete"` のいずれか。
            `"read"` を含む他の値は False（タイポ防止）。
    """
    import asyncio

    if ctx is None:
        return False

    # 未知 action は許可しない（タイポ防止）
    if required_action not in _ACTION_REQUIRED_SCOPE:
        return False
    required_scope = _ACTION_REQUIRED_SCOPE[required_action]
    if not ctx.has_scope(required_scope):
        return False

    owner_id = tileset.get("user_id")
    if owner_id and ctx.user_id == str(owner_id):
        return True

    tileset_id = str(tileset["id"])

    if ctx.is_api_key:
        if ctx.team_id is None:
            return False
        return await asyncio.to_thread(
            _team_permission_allows, conn, ctx.team_id, tileset_id, required_action
        )

    return await asyncio.to_thread(
        _user_can_perform_action, conn, ctx.user_id, tileset_id, required_action
    )


def _user_can_perform_action(
    conn, user_id: str, tileset_id: str, action: str
) -> bool:
    """`can_user_perform_action()` SQL 関数を呼び出す（JWT ユーザー用）。"""
    import psycopg2
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT can_user_perform_action(%s::uuid, %s::uuid, %s)",
                (user_id, tileset_id, action),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False
    except psycopg2.errors.InvalidTextRepresentation:
        # 不正な UUID 形式
        conn.rollback()
        return False


def _team_permission_allows(
    conn, team_id: str, tileset_id: str, action: str
) -> bool:
    """team_tilesets.permission_level だけで action 可否を判定（API キー用）。

    team_role の継承（owner→admin 等）は適用しない。team_tilesets に紐付け
    が無ければ False。
    """
    import psycopg2
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT permission_level FROM team_tilesets
                  WHERE team_id = %s AND tileset_id = %s LIMIT 1""",
                (team_id, tileset_id),
            )
            row = cur.fetchone()
            if not row:
                return False
            level = row[0]
            # 呼び出し元 (`check_tileset_write_access_v2`) で
            # `_ACTION_REQUIRED_SCOPE` (`{create, update, delete}`) に絞って
            # validate 済み。read は別ヘルパ (`check_tileset_access_v2`) を使う。
            if action in ("create", "update"):
                return level in ("write", "admin")
            if action == "delete":
                return level == "admin"
            return False
    except psycopg2.errors.InvalidTextRepresentation:
        conn.rollback()
        return False


__all__ = [
    # Models
    "User", "AuthResult", "TokenPair",
    # Errors
    "AuthError", "InvalidCredentials", "RateLimited", "UserNotFound",
    "UserAlreadyExists", "InvalidToken", "WeakPassword", "ProviderError",
    # Provider
    "AuthProvider", "get_auth_provider",
    # Dependencies (legacy JWT-only)
    "get_current_user", "require_auth",
    # Helpers
    "extract_token_from_header", "verify_jwt_token",
    "is_auth_configured",
    # Unified context for JWT + API key (Task 3.2)
    "AuthContext", "validate_api_key", "API_KEY_PREFIX", "log_api_key_request",
    "get_auth_context_optional", "require_auth_context",
    # Tileset authorization (team-aware, ctx-based)
    "check_tileset_access_v2",
    # NEW (issue #49 / C-1): team-based tileset write authorization
    "check_tileset_write_access_v2",
]
