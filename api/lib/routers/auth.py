"""認証関連エンドポイント。"""
from datetime import datetime
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from lib.auth import (
    User, AuthContext, AuthError,
    InvalidCredentials, RateLimited, InvalidToken,
    UserAlreadyExists, UserNotFound, WeakPassword, ProviderError,
    require_auth, get_auth_provider,
)
from lib.config import get_settings
from lib.database import get_connection, get_db_connection


router = APIRouter(prefix="/api/auth", tags=["auth"])


# === エラー翻訳 ===

ERROR_MAP = {
    InvalidCredentials: 401,
    RateLimited: 429,
    InvalidToken: 401,
    UserAlreadyExists: 409,
    UserNotFound: 404,
    WeakPassword: 400,
    ProviderError: 502,
}


def _translate(e: AuthError) -> HTTPException:
    code = ERROR_MAP.get(type(e), 500)
    return HTTPException(status_code=code, detail=str(e))


# === Cookie ヘルパ ===

REFRESH_COOKIE_NAME = "geo_base_refresh"
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        # Path="/" にすることで Admin UI 側 middleware が Cookie の存在を
        # 検査できる。トークンは HttpOnly なので JS から読めず、
        # 認証時のみ /api/auth/refresh で実際の検証が走るため安全性は維持。
        path="/",
        domain=settings.cookie_domain or None,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        domain=settings.cookie_domain or None,
    )


def _check_origin(request: Request) -> None:
    """state-changing endpoint で Origin ヘッダ検証"""
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(403, "Origin not allowed")


# ===========================================================================
# 1. POST /login
# ===========================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
):
    """email + password でログイン。"""
    provider = get_auth_provider()
    try:
        pair = await provider.authenticate(
            body.email, body.password,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        raise _translate(e)

    user = await provider.get_user_by_email(body.email)
    _set_refresh_cookie(response, pair.refresh_token)
    return LoginResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
    )


# ===========================================================================
# 2. POST /refresh
# ===========================================================================

class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: Request, response: Response):
    _check_origin(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(401, "No refresh token")
    try:
        pair = await get_auth_provider().refresh_tokens(
            refresh_token,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        _clear_refresh_cookie(response)
        raise _translate(e)

    # Decode access_token to get user_id
    from lib.auth.jwt_utils import decode_access_token
    settings = get_settings()
    claims = decode_access_token(
        pair.access_token,
        secret=settings.effective_jwt_secret,
        audience=settings.jwt_audience,
    )
    user_id = claims["sub"]
    user = await get_auth_provider().get_user_by_id(user_id)
    _set_refresh_cookie(response, pair.refresh_token)
    return RefreshResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
    )


# ===========================================================================
# 3. POST /logout
# ===========================================================================

@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    _check_origin(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            await get_auth_provider().revoke_refresh_token(refresh_token)
        except AuthError:
            pass
    _clear_refresh_cookie(response)


# ===========================================================================
# 4. GET /me
# ===========================================================================

@router.get("/me", response_model=User)
async def get_me(user: User = Depends(require_auth)):
    return user


# ===========================================================================
# 5. PATCH /me
# ===========================================================================

class UpdateMeRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    user_metadata: Optional[dict] = None


@router.patch("/me", response_model=User)
async def update_me(body: UpdateMeRequest, user: User = Depends(require_auth)):
    try:
        return await get_auth_provider().update_user(
            user.id, name=body.name, email=body.email, user_metadata=body.user_metadata,
        )
    except AuthError as e:
        raise _translate(e)


# ===========================================================================
# 6. POST /me/password
# ===========================================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.post("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(require_auth),
):
    provider = get_auth_provider()
    # 現パスワード検証: authenticate でログイン試行
    try:
        await provider.authenticate(user.email, body.current_password)
    except AuthError:
        raise HTTPException(401, "Invalid current password")
    try:
        await provider.update_password(user.id, body.new_password)
    except AuthError as e:
        raise _translate(e)

    # 全 refresh token を失効
    from lib.auth.tokens import revoke_all_user_tokens
    with get_db_connection() as conn:
        revoke_all_user_tokens(conn, user.id, reason="password_changed")


# ===========================================================================
# 7. POST /password-reset/request
# ===========================================================================

class PasswordResetRequestModel(BaseModel):
    email: EmailStr


@router.post("/password-reset/request", status_code=204)
async def password_reset_request(body: PasswordResetRequestModel, request: Request):
    try:
        await get_auth_provider().request_password_reset(
            body.email,
            ip=request.client.host if request.client else None,
        )
    except AuthError:
        pass  # 情報漏洩防止のため常に 204


# ===========================================================================
# 8. POST /password-reset/confirm
# ===========================================================================

class PasswordResetConfirmModel(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)


@router.post("/password-reset/confirm", status_code=204)
async def password_reset_confirm(body: PasswordResetConfirmModel):
    try:
        await get_auth_provider().confirm_password_reset(body.token, body.new_password)
    except AuthError as e:
        raise _translate(e)


# ===========================================================================
# 9. GET /invitations/{token}
# ===========================================================================

class InvitationInfoResponse(BaseModel):
    team_id: str
    team_name: str
    team_slug: str
    role: str
    email: str
    inviter_name: Optional[str] = None
    expires_at: datetime
    has_existing_account: bool


@router.get("/invitations/{token}", response_model=InvitationInfoResponse)
async def get_invitation(token: str, conn=Depends(get_connection)):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT i.team_id, t.name, t.slug, i.role, i.email, i.expires_at, i.status,
                      u_inviter.name AS inviter_name
               FROM team_invitations i
               JOIN teams t ON i.team_id = t.id
               LEFT JOIN users u_inviter ON u_inviter.id = i.invited_by
               WHERE i.token = %s""",
            (token,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Invitation not found")

    team_id, team_name, team_slug, role, email, expires_at, status_, inviter_name = row
    if status_ != "pending":
        raise HTTPException(404, f"Invitation is {status_}")

    # Compare expires_at to current time, handling timezone
    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    if expires_at.tzinfo is None:
        # If naive, assume UTC
        expires_at_aware = expires_at.replace(tzinfo=_tz.utc)
    else:
        expires_at_aware = expires_at
    if expires_at_aware < now:
        raise HTTPException(404, "Invitation expired")

    existing = await get_auth_provider().get_user_by_email(email)
    return InvitationInfoResponse(
        team_id=str(team_id), team_name=team_name, team_slug=team_slug,
        role=role, email=email, inviter_name=inviter_name,
        expires_at=expires_at,
        has_existing_account=existing is not None,
    )


# ===========================================================================
# 10. POST /accept-invitation
# ===========================================================================

class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)
    name: Optional[str] = Field(None, max_length=255)


class AcceptInvitationResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: User
    team_member: dict


@router.post("/accept-invitation", response_model=AcceptInvitationResponse, status_code=201)
async def accept_invitation(
    body: AcceptInvitationRequest,
    response: Response,
    request: Request,
    conn=Depends(get_connection),
):
    # 招待検証
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, team_id, email, role, expires_at, status
               FROM team_invitations WHERE token = %s FOR UPDATE""",
            (body.token,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(400, "Invalid invitation token")
    inv_id, team_id, email, role, expires_at, status_ = row

    if status_ != "pending":
        raise HTTPException(400, f"Invitation is {status_}")

    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    if expires_at.tzinfo is None:
        expires_at_aware = expires_at.replace(tzinfo=_tz.utc)
    else:
        expires_at_aware = expires_at
    if expires_at_aware < now:
        raise HTTPException(400, "Invitation has expired")

    provider = get_auth_provider()

    # 既存ユーザーチェック
    existing = await provider.get_user_by_email(email)
    if existing is not None:
        raise HTTPException(409, "An account with this email already exists. Please log in and accept via /api/teams/invitations/accept")

    # ユーザー作成
    try:
        user = await provider.create_user(
            email=email, password=body.password, name=body.name,
            email_verified=True,
        )
    except AuthError as e:
        raise _translate(e)

    # team_members 追加 + 招待を accepted に更新（同一トランザクション）
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO team_members (team_id, user_id, role)
               VALUES (%s, %s, %s)""",
            (team_id, user.id, role),
        )
        cur.execute(
            "UPDATE team_invitations SET status = 'accepted', accepted_at = NOW() WHERE id = %s",
            (inv_id,),
        )
    conn.commit()

    # ログイン状態にする
    pair = await provider.authenticate(
        email, body.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, pair.refresh_token)
    return AcceptInvitationResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=user,
        team_member={"team_id": str(team_id), "role": role},
    )
