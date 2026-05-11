"""
API Keys CRUD endpoints and management.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from lib.config import get_settings
from lib.database import get_connection
from lib.errors import ErrorCode, api_error
from lib.auth import User, get_current_user, require_auth
from lib.models.api_key import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyRevoke,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyUsageStats,
    ApiKeyUsageLogResponse,
    ApiKeyUsageLogEntry,
    ApiKeyUsageDay,
    RateLimitStatus,
    ApiKeyScope,
    generate_api_key,
    hash_api_key,
)


router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])
settings = get_settings()


# =============================================================================
# Helper Functions
# =============================================================================

def get_api_key_or_404(conn, key_id: str, user_id: str) -> dict:
    """Get an API key by ID, ensuring ownership."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, description, prefix, user_id, team_id, scopes,
                      rate_limit_per_minute, rate_limit_per_day, is_active,
                      last_used_at, expires_at, revoked_at, created_at, updated_at,
                      metadata
               FROM api_keys WHERE id = %s""",
            (key_id,)
        )
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
    
    if not row:
        raise api_error(
            404,
            ErrorCode.API_KEY_NOT_FOUND,
            f"API key not found: {key_id}",
            details={"key_id": key_id},
        )

    key_data = dict(zip(columns, row))

    # Check ownership (user must own the key or be team admin)
    if str(key_data['user_id']) != user_id:
        # Check if user is team admin
        if key_data['team_id']:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT role FROM team_members
                       WHERE team_id = %s AND user_id = %s AND role IN ('owner', 'administrator')""",
                    (key_data['team_id'], user_id)
                )
                if not cur.fetchone():
                    raise api_error(
                        403,
                        ErrorCode.API_KEY_FORBIDDEN,
                        "You don't have permission to access this API key",
                        details={"key_id": key_id},
                    )
        else:
            raise api_error(
                403,
                ErrorCode.API_KEY_FORBIDDEN,
                "You don't have permission to access this API key",
                details={"key_id": key_id},
            )
    
    return key_data


def serialize_api_key(key_data: dict, include_team_name: bool = False) -> dict:
    """Serialize API key data for response."""
    result = {}
    for key, value in key_data.items():
        if value is None:
            result[key] = None
        elif key in ('id', 'user_id', 'team_id', 'revoked_by'):
            result[key] = str(value) if value else None
        elif key in ('created_at', 'updated_at', 'last_used_at', 'expires_at', 'revoked_at'):
            result[key] = value.isoformat() if value else None
        elif key == 'scopes' and isinstance(value, list):
            result[key] = value
        elif key == 'metadata':
            result[key] = value if value else {}
        else:
            result[key] = value
    return result


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    key_data: ApiKeyCreate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """
    Create a new API key.
    
    The full key is only returned once - make sure to save it!
    """
    try:
        # If team_id provided, verify user is a team member
        if key_data.team_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                    (key_data.team_id, user.id)
                )
                if not cur.fetchone():
                    raise api_error(
                        403,
                        ErrorCode.TEAM_FORBIDDEN,
                        "You are not a member of this team",
                        details={"team_id": str(key_data.team_id)},
                    )
        
        # Generate the API key
        full_key, prefix, key_hash = generate_api_key(key_data.environment)
        
        # Calculate expiration
        expires_at = None
        if key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
        
        # Convert scopes to list of strings
        scopes = [s.value for s in key_data.scopes]

        # JSONB バインドは json.dumps + ::jsonb キャストで行う。psycopg2 は dict を
        # JSONB に直接 adapt できず "can't adapt type 'dict'" になるため、本リポジトリ
        # の他の JSONB 書き込み (tilesets / teams / users 等) と同じパターンに揃える。
        metadata_json = json.dumps(key_data.metadata) if key_data.metadata else "{}"

        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_keys (
                       name, description, prefix, key_hash, user_id, team_id,
                       scopes, rate_limit_per_minute, rate_limit_per_day,
                       expires_at, metadata
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                   RETURNING id, name, description, prefix, user_id, team_id,
                             scopes, rate_limit_per_minute, rate_limit_per_day,
                             is_active, last_used_at, expires_at, revoked_at,
                             created_at, updated_at""",
                (
                    key_data.name,
                    key_data.description,
                    prefix,
                    key_hash,
                    user.id,
                    key_data.team_id,
                    scopes,
                    key_data.rate_limit_per_minute,
                    key_data.rate_limit_per_day,
                    expires_at,
                    metadata_json,
                )
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        result = serialize_api_key(dict(zip(columns, row)))
        result['key'] = full_key  # Include the actual key in response
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error creating API key: {str(e)}",
        )


@router.get("", response_model=ApiKeyListResponse)
def list_api_keys(
    conn=Depends(get_connection),
    user: User = Depends(require_auth),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    include_revoked: bool = Query(False, description="Include revoked keys"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List API keys for the current user or team."""
    try:
        offset = (page - 1) * page_size
        
        # Build query
        conditions = ["(ak.user_id = %s"]
        params = [user.id]
        
        # Also include keys for teams user is a member of
        conditions[0] += " OR ak.team_id IN (SELECT team_id FROM team_members WHERE user_id = %s))"
        params.append(user.id)
        
        if team_id:
            conditions.append("ak.team_id = %s")
            params.append(team_id)
        
        if not include_revoked:
            conditions.append("ak.revoked_at IS NULL")
        
        where_clause = " AND ".join(conditions)
        
        with conn.cursor() as cur:
            # Get total count
            cur.execute(
                f"SELECT COUNT(*) FROM api_keys ak WHERE {where_clause}",
                tuple(params)
            )
            total = cur.fetchone()[0]
            
            # Get keys
            cur.execute(
                f"""SELECT ak.id, ak.name, ak.description, ak.prefix, ak.user_id, ak.team_id,
                           ak.scopes, ak.rate_limit_per_minute, ak.rate_limit_per_day,
                           ak.is_active, ak.last_used_at, ak.expires_at, ak.revoked_at,
                           ak.created_at, ak.updated_at, t.name as team_name
                    FROM api_keys ak
                    LEFT JOIN teams t ON ak.team_id = t.id
                    WHERE {where_clause}
                    ORDER BY ak.created_at DESC
                    LIMIT %s OFFSET %s""",
                tuple(params + [page_size, offset])
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        keys = [serialize_api_key(dict(zip(columns, row))) for row in rows]
        
        return {
            "keys": keys,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error listing API keys: {str(e)}",
        )


@router.get("/{key_id}", response_model=ApiKeyResponse)
def get_api_key(
    key_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Get details of a specific API key."""
    try:
        key_data = get_api_key_or_404(conn, key_id, user.id)
        
        # Get team name if applicable
        if key_data.get('team_id'):
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM teams WHERE id = %s", (key_data['team_id'],))
                row = cur.fetchone()
                if row:
                    key_data['team_name'] = row[0]
        
        return serialize_api_key(key_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error fetching API key: {str(e)}",
        )


@router.put("/{key_id}", response_model=ApiKeyResponse)
def update_api_key(
    key_id: str,
    update_data: ApiKeyUpdate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Update an API key's settings."""
    try:
        # Verify ownership
        get_api_key_or_404(conn, key_id, user.id)
        
        updates = []
        params = []
        
        if update_data.name is not None:
            updates.append("name = %s")
            params.append(update_data.name)
        
        if update_data.description is not None:
            updates.append("description = %s")
            params.append(update_data.description)
        
        if update_data.scopes is not None:
            updates.append("scopes = %s")
            params.append([s.value for s in update_data.scopes])
        
        if update_data.rate_limit_per_minute is not None:
            updates.append("rate_limit_per_minute = %s")
            params.append(update_data.rate_limit_per_minute)
        
        if update_data.rate_limit_per_day is not None:
            updates.append("rate_limit_per_day = %s")
            params.append(update_data.rate_limit_per_day)
        
        if update_data.is_active is not None:
            updates.append("is_active = %s")
            params.append(update_data.is_active)
        
        if update_data.metadata is not None:
            # create_api_key と同じく JSONB バインドは json.dumps + ::jsonb キャスト
            updates.append("metadata = %s::jsonb")
            params.append(json.dumps(update_data.metadata))
        
        if not updates:
            raise api_error(
                400,
                ErrorCode.VALIDATION_FIELD_REQUIRED,
                "No fields to update",
            )
        
        params.append(key_id)
        
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE api_keys SET {', '.join(updates)}, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, description, prefix, user_id, team_id,
                              scopes, rate_limit_per_minute, rate_limit_per_day,
                              is_active, last_used_at, expires_at, revoked_at,
                              created_at, updated_at""",
                tuple(params)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        return serialize_api_key(dict(zip(columns, row)))
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error updating API key: {str(e)}",
        )


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse)
def revoke_api_key(
    key_id: str,
    revoke_data: ApiKeyRevoke,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Revoke an API key (cannot be undone)."""
    try:
        key_data = get_api_key_or_404(conn, key_id, user.id)
        
        if key_data.get('revoked_at'):
            raise api_error(
                400,
                ErrorCode.API_KEY_REVOKED,
                "API key is already revoked",
                details={"key_id": key_id},
            )
        
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE api_keys 
                   SET revoked_at = NOW(), revoked_by = %s, revoke_reason = %s,
                       is_active = false, updated_at = NOW()
                   WHERE id = %s
                   RETURNING id, name, description, prefix, user_id, team_id,
                             scopes, rate_limit_per_minute, rate_limit_per_day,
                             is_active, last_used_at, expires_at, revoked_at,
                             created_at, updated_at""",
                (user.id, revoke_data.reason, key_id)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        return serialize_api_key(dict(zip(columns, row)))
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error revoking API key: {str(e)}",
        )


@router.delete("/{key_id}", status_code=204)
def delete_api_key(
    key_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Permanently delete an API key."""
    try:
        # Verify ownership
        get_api_key_or_404(conn, key_id, user.id)
        
        with conn.cursor() as cur:
            cur.execute("DELETE FROM api_keys WHERE id = %s", (key_id,))
            if cur.rowcount == 0:
                raise api_error(
                    404,
                    ErrorCode.API_KEY_NOT_FOUND,
                    "API key not found",
                    details={"key_id": key_id},
                )

        conn.commit()

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error deleting API key: {str(e)}",
        )


# =============================================================================
# Usage & Statistics Endpoints
# =============================================================================

@router.get("/{key_id}/usage", response_model=ApiKeyUsageStats)
def get_api_key_usage(
    key_id: str,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Get usage statistics for an API key."""
    try:
        # Verify ownership
        get_api_key_or_404(conn, key_id, user.id)
        
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_api_key_usage_stats(%s, %s)",
                (key_id, days)
            )
            row = cur.fetchone()
        
        if row:
            total_requests, avg_response_time, error_count, success_rate, requests_by_day = row
            
            # Parse requests_by_day
            daily_stats = []
            if requests_by_day:
                for day in requests_by_day:
                    daily_stats.append(ApiKeyUsageDay(
                        date=str(day.get('date', '')),
                        requests=day.get('requests', 0),
                        errors=day.get('errors', 0),
                        avg_response_time=day.get('avg_response_time', 0)
                    ))
            
            return ApiKeyUsageStats(
                key_id=key_id,
                total_requests=total_requests or 0,
                avg_response_time_ms=float(avg_response_time or 0),
                error_count=error_count or 0,
                success_rate=float(success_rate or 100),
                requests_by_day=daily_stats
            )
        
        return ApiKeyUsageStats(
            key_id=key_id,
            total_requests=0,
            avg_response_time_ms=0,
            error_count=0,
            success_rate=100,
            requests_by_day=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error fetching usage stats: {str(e)}",
        )


@router.get("/{key_id}/logs", response_model=ApiKeyUsageLogResponse)
def get_api_key_logs(
    key_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Get usage logs for an API key."""
    try:
        # Verify ownership
        get_api_key_or_404(conn, key_id, user.id)
        
        offset = (page - 1) * page_size
        
        with conn.cursor() as cur:
            # Get total count
            cur.execute(
                "SELECT COUNT(*) FROM api_key_usage_logs WHERE api_key_id = %s",
                (key_id,)
            )
            total = cur.fetchone()[0]
            
            # Get logs
            cur.execute(
                """SELECT id, endpoint, method, status_code, response_time_ms,
                          ip_address::TEXT, created_at
                   FROM api_key_usage_logs
                   WHERE api_key_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                (key_id, page_size, offset)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        logs = []
        for row in rows:
            log_data = dict(zip(columns, row))
            logs.append(ApiKeyUsageLogEntry(
                id=str(log_data['id']),
                endpoint=log_data['endpoint'],
                method=log_data['method'],
                status_code=log_data['status_code'],
                response_time_ms=log_data['response_time_ms'],
                ip_address=log_data['ip_address'],
                created_at=log_data['created_at']
            ))
        
        return ApiKeyUsageLogResponse(
            logs=logs,
            total=total,
            key_id=key_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error fetching usage logs: {str(e)}",
        )


@router.get("/{key_id}/rate-limit", response_model=RateLimitStatus)
def get_rate_limit_status(
    key_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Get current rate limit status for an API key."""
    try:
        key_data = get_api_key_or_404(conn, key_id, user.id)
        
        with conn.cursor() as cur:
            # Get minute status
            cur.execute(
                "SELECT * FROM get_api_key_rate_limit_status(%s, 'minute')",
                (key_id,)
            )
            minute_row = cur.fetchone()
            
            # Get day status
            cur.execute(
                "SELECT * FROM get_api_key_rate_limit_status(%s, 'day')",
                (key_id,)
            )
            day_row = cur.fetchone()
        
        minute_used = minute_row[0] if minute_row else 0
        minute_limit = key_data['rate_limit_per_minute']
        day_used = day_row[0] if day_row else 0
        day_limit = key_data['rate_limit_per_day']
        
        return RateLimitStatus(
            key_id=key_id,
            minute_limit=minute_limit,
            minute_used=minute_used,
            minute_remaining=max(0, minute_limit - minute_used),
            day_limit=day_limit,
            day_used=day_used,
            day_remaining=max(0, day_limit - day_used)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(
            500,
            ErrorCode.INTERNAL_DB_ERROR,
            f"Error fetching rate limit status: {str(e)}",
        )


# =============================================================================
# Validation Endpoint (for external services)
# =============================================================================

@router.post("/validate")
def validate_api_key_endpoint(
    request: Request,
    conn=Depends(get_connection)
):
    """
    Validate an API key (used internally or by external services).
    
    Send the API key in the X-API-Key header.
    """
    try:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"valid": False, "error": "No API key provided"}
            )
        
        key_hash = hash_api_key(api_key)
        
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, team_id, scopes, rate_limit_per_minute, rate_limit_per_day
                   FROM api_keys
                   WHERE key_hash = %s
                     AND is_active = true
                     AND revoked_at IS NULL
                     AND (expires_at IS NULL OR expires_at > NOW())""",
                (key_hash,)
            )
            row = cur.fetchone()
        
        if not row:
            return JSONResponse(
                status_code=401,
                content={"valid": False, "error": "Invalid or expired API key"}
            )
        
        key_id, user_id, team_id, scopes, rate_limit_minute, rate_limit_day = row
        
        # Update last used
        with conn.cursor() as cur:
            cur.execute("SELECT update_api_key_last_used(%s)", (key_id,))
        conn.commit()
        
        return {
            "valid": True,
            "key_id": str(key_id),
            "user_id": str(user_id),
            "team_id": str(team_id) if team_id else None,
            "scopes": scopes,
            "rate_limit_per_minute": rate_limit_minute,
            "rate_limit_per_day": rate_limit_day
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"valid": False, "error": str(e)}
        )
