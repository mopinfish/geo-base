"""
Authentication utilities for geo-base API.

Features:
- Supabase Auth JWT token verification
- User extraction from JWT claims
- Optional authentication dependency for public/private resources
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Header, status
from pydantic import BaseModel

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from lib.config import get_settings


# =============================================================================
# Models
# =============================================================================


class User(BaseModel):
    """Authenticated user model extracted from JWT."""
    id: str  # Supabase user ID (sub claim)
    email: Optional[str] = None
    role: Optional[str] = None  # e.g., "authenticated", "anon"
    
    # Additional metadata from JWT
    app_metadata: Optional[dict] = None
    user_metadata: Optional[dict] = None


class AuthResult(BaseModel):
    """Authentication result with user and authentication status."""
    is_authenticated: bool
    user: Optional[User] = None
    error: Optional[str] = None


# =============================================================================
# JWT Verification
# =============================================================================


def verify_jwt_token(token: str) -> AuthResult:
    """
    Verify a Supabase JWT token and extract user information.
    
    Args:
        token: JWT token string (without 'Bearer ' prefix)
        
    Returns:
        AuthResult with user info if valid, error message if invalid
    """
    settings = get_settings()
    
    if not settings.supabase_jwt_secret:
        return AuthResult(
            is_authenticated=False,
            error="JWT secret not configured"
        )
    
    try:
        # Decode and verify the JWT
        # Supabase uses HS256 algorithm by default
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase default audience
        )
        
        # Extract user information from claims
        user = User(
            id=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role"),
            app_metadata=payload.get("app_metadata"),
            user_metadata=payload.get("user_metadata"),
        )
        
        return AuthResult(
            is_authenticated=True,
            user=user
        )
        
    except ExpiredSignatureError:
        return AuthResult(
            is_authenticated=False,
            error="Token has expired"
        )
    except InvalidTokenError as e:
        return AuthResult(
            is_authenticated=False,
            error=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        return AuthResult(
            is_authenticated=False,
            error=f"Authentication error: {str(e)}"
        )


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string or None if invalid format
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    
    if len(parts) != 2:
        return None
    
    scheme, token = parts
    
    if scheme.lower() != "bearer":
        return None
    
    return token


# =============================================================================
# FastAPI Dependencies
# =============================================================================


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None
) -> Optional[User]:
    """
    FastAPI dependency to get the current authenticated user.
    
    Returns None if no valid authentication is provided.
    Does not raise an exception for unauthenticated requests.
    
    Usage:
        @app.get("/api/resource")
        def get_resource(user: Optional[User] = Depends(get_current_user)):
            if user:
                # Authenticated request
            else:
                # Anonymous request
    """
    if not authorization:
        return None
    
    token = extract_token_from_header(authorization)
    if not token:
        return None
    
    result = verify_jwt_token(token)
    
    if result.is_authenticated and result.user:
        return result.user
    
    return None


async def require_auth(
    authorization: Annotated[Optional[str], Header()] = None
) -> User:
    """
    FastAPI dependency that requires authentication.
    
    Raises HTTPException 401 if not authenticated.
    
    Usage:
        @app.get("/api/protected")
        def protected_resource(user: User = Depends(require_auth)):
            # Only authenticated users reach here
    """
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
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = verify_jwt_token(token)
    
    if not result.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not extract user from token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return result.user


# =============================================================================
# Tileset Access Control
# =============================================================================


def check_tileset_access(
    tileset_id: str,
    is_public: bool,
    owner_user_id: Optional[str],
    current_user: Optional[User],
) -> bool:
    """
    Check if the current user has access to a tileset.
    
    Access rules:
    - Public tilesets (is_public=True): Anyone can access
    - Private tilesets (is_public=False): Only the owner can access
    
    Args:
        tileset_id: ID of the tileset
        is_public: Whether the tileset is public
        owner_user_id: User ID of the tileset owner
        current_user: Currently authenticated user (or None)
        
    Returns:
        True if access is allowed, False otherwise
    """
    # Public tilesets are accessible to everyone
    if is_public:
        return True
    
    # Private tilesets require authentication
    if not current_user:
        return False
    
    # Private tilesets are only accessible to the owner
    if owner_user_id and current_user.id == owner_user_id:
        return True
    
    return False


async def get_tileset_with_access_check(
    tileset_id: str,
    conn,
    current_user: Optional[User],
) -> dict:
    """
    Get tileset from database and check access permissions.
    
    Args:
        tileset_id: ID of the tileset
        conn: Database connection
        current_user: Currently authenticated user (or None)
        
    Returns:
        Tileset data dictionary
        
    Raises:
        HTTPException: 404 if not found, 401 if auth required, 403 if forbidden
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, type, format, min_zoom, max_zoom,
                   is_public, user_id, metadata, created_at, updated_at
            FROM tilesets
            WHERE id = %s
            """,
            (tileset_id,),
        )
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tileset not found: {tileset_id}"
        )
    
    tileset = dict(zip(columns, row))
    is_public = tileset.get("is_public", True)
    owner_user_id = str(tileset.get("user_id")) if tileset.get("user_id") else None
    
    # Check access
    if not is_public and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this tileset",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not check_tileset_access(tileset_id, is_public, owner_user_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this tileset"
        )
    
    return tileset


# =============================================================================
# Utility Functions
# =============================================================================


def is_auth_configured() -> bool:
    """Check if authentication is properly configured."""
    settings = get_settings()
    return bool(settings.supabase_jwt_secret)
