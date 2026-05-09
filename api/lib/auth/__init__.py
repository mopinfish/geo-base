"""auth パッケージ。

公開シンボル:
- User, AuthResult, TokenPair: モデル
- AuthError 系: エラー階層
- AuthProvider: 抽象インタフェース
- get_auth_provider(): factory
- require_auth, get_current_user: FastAPI dependencies (既存互換)
- verify_jwt_token: 後方互換用エイリアス
- extract_token_from_header: 既存ヘルパ
- check_tileset_access, get_tileset_with_access_check, is_auth_configured: 既存タイル系認可
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


# === 既存タイル認可関数（既存 auth.py から移設） ===

def check_tileset_access(
    tileset_id: str,
    is_public: bool,
    owner_user_id: Optional[str],
    current_user: Optional[User],
) -> bool:
    """旧来のタイルセットアクセスチェック（後方互換）。

    新規コードは AuthContext + check_tileset_access_v2 を使うこと。
    """
    if is_public:
        return True
    if not current_user:
        return False
    if owner_user_id and current_user.id == owner_user_id:
        return True
    return False


async def get_tileset_with_access_check(
    tileset_id: str,
    conn,
    current_user: Optional[User],
) -> dict:
    """既存 auth.py から移設。新規コードは AuthContext 版を使うこと。"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, description, type, format, min_zoom, max_zoom,
                      is_public, user_id, metadata, created_at, updated_at
               FROM tilesets WHERE id = %s""",
            (tileset_id,),
        )
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, f"Tileset not found: {tileset_id}")

    tileset = dict(zip(columns, row))
    is_public = tileset.get("is_public", True)
    owner_user_id = str(tileset.get("user_id")) if tileset.get("user_id") else None

    if not is_public and not current_user:
        raise HTTPException(401, "Authentication required to access this tileset",
                            headers={"WWW-Authenticate": "Bearer"})

    if not check_tileset_access(tileset_id, is_public, owner_user_id, current_user):
        raise HTTPException(403, "You do not have permission to access this tileset")

    return tileset


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
    # Tile access (legacy)
    "check_tileset_access", "get_tileset_with_access_check", "is_auth_configured",
    # NEW (Task 3.2): unified context for JWT + API key
    "AuthContext", "validate_api_key", "API_KEY_PREFIX", "log_api_key_request",
    "get_auth_context_optional", "require_auth_context",
    # NEW (Task 3.3): team-based tileset authorization
    "check_tileset_access_v2",
]
