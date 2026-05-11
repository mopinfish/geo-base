"""
Teams management CRUD endpoints.
"""

from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from lib.config import get_settings
from lib.database import get_connection
from lib.auth import User, get_current_user, require_auth
from lib.models.team import (
    TeamRole,
    InvitationStatus,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
    TeamMemberAdd,
    TeamMemberUpdate,
    TeamMemberResponse,
    TeamMemberListResponse,
    TeamInvitationCreate,
    TeamInvitationResponse,
    TeamInvitationAccept,
    TeamInvitationListResponse,
    TeamTilesetAdd,
    TeamTilesetResponse,
    TeamTilesetListResponse,
    TeamOwnershipTransfer,
)


router = APIRouter(prefix="/api/teams", tags=["teams"])
settings = get_settings()


# =============================================================================
# Helper Functions
# =============================================================================

def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from team name."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    # Add random suffix for uniqueness
    suffix = secrets.token_hex(4)
    return f"{slug}-{suffix}" if slug else suffix


def generate_invitation_token() -> str:
    """Generate a secure invitation token."""
    return secrets.token_urlsafe(32)


def get_user_role_in_team(conn, team_id: str, user_id: str) -> Optional[TeamRole]:
    """Get user's role in a team."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
            (team_id, user_id)
        )
        row = cur.fetchone()
        if row:
            return TeamRole(row[0])
    return None


def check_team_permission(conn, team_id: str, user_id: str, required_roles: list[TeamRole]) -> bool:
    """Check if user has required role in team."""
    role = get_user_role_in_team(conn, team_id, user_id)
    return role in required_roles if role else False


def get_team_or_404(conn, team_id: str) -> dict:
    """Get team by ID or raise 404."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, slug, description, owner_id, settings, created_at, updated_at
               FROM teams WHERE id = %s""",
            (team_id,)
        )
        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
    
    return dict(zip(columns, row))


def serialize_team(team_data: dict) -> dict:
    """Serialize team data for response."""
    result = {}
    for key, value in team_data.items():
        if value is None:
            result[key] = None
        elif key in ('id', 'owner_id'):
            result[key] = str(value)
        elif key in ('created_at', 'updated_at'):
            result[key] = value.isoformat() if value else None
        elif key == 'settings':
            result[key] = value if value else {}
        else:
            result[key] = value
    return result


# =============================================================================
# Team CRUD Endpoints
# =============================================================================

@router.post("", response_model=TeamResponse, status_code=201)
def create_team(
    team_data: TeamCreate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Create a new team."""
    import json
    
    try:
        slug = team_data.slug or generate_slug(team_data.name)
        settings_json = json.dumps(team_data.settings) if team_data.settings else '{}'
        
        with conn.cursor() as cur:
            # Check if slug already exists
            cur.execute("SELECT id FROM teams WHERE slug = %s", (slug,))
            if cur.fetchone():
                slug = generate_slug(team_data.name)
            
            # Create team
            cur.execute(
                """INSERT INTO teams (name, slug, description, owner_id, settings)
                   VALUES (%s, %s, %s, %s, %s::jsonb)
                   RETURNING id, name, slug, description, owner_id, settings, created_at, updated_at""",
                (team_data.name, slug, team_data.description, user.id, settings_json)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            team = dict(zip(columns, row))
            
            # Add creator as owner member (with conflict handling)
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, 'owner')
                   ON CONFLICT (team_id, user_id) DO NOTHING""",
                (team['id'], user.id)
            )
        
        conn.commit()
        
        result = serialize_team(team)
        result['member_count'] = 1
        result['tileset_count'] = 0
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating team: {str(e)}")


@router.get("", response_model=TeamListResponse)
def list_teams(
    conn=Depends(get_connection),
    user: User = Depends(require_auth),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List teams the user is a member of."""
    try:
        offset = (page - 1) * page_size
        
        with conn.cursor() as cur:
            # Get total count
            cur.execute(
                """SELECT COUNT(*) FROM teams t
                   JOIN team_members tm ON t.id = tm.team_id
                   WHERE tm.user_id = %s""",
                (user.id,)
            )
            total = cur.fetchone()[0]
            
            # Get teams with counts
            cur.execute(
                """SELECT t.id, t.name, t.slug, t.description, t.owner_id, t.settings,
                          t.created_at, t.updated_at,
                          (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) as member_count,
                          (SELECT COUNT(*) FROM team_tilesets WHERE team_id = t.id) as tileset_count
                   FROM teams t
                   JOIN team_members tm ON t.id = tm.team_id
                   WHERE tm.user_id = %s
                   ORDER BY t.created_at DESC
                   LIMIT %s OFFSET %s""",
                (user.id, page_size, offset)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        teams = [serialize_team(dict(zip(columns, row))) for row in rows]
        
        return {
            "teams": teams,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing teams: {str(e)}")


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Get team details."""
    try:
        team = get_team_or_404(conn, team_id)
        
        # Check if user is a member
        if not check_team_permission(conn, team_id, user.id, 
                                     [TeamRole.OWNER, TeamRole.ADMINISTRATOR, TeamRole.MEMBER, TeamRole.GUEST]):
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        
        # Get counts
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM team_members WHERE team_id = %s", (team_id,))
            member_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM team_tilesets WHERE team_id = %s", (team_id,))
            tileset_count = cur.fetchone()[0]
        
        result = serialize_team(team)
        result['member_count'] = member_count
        result['tileset_count'] = tileset_count
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team: {str(e)}")


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: str,
    update_data: TeamUpdate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Update team details."""
    import json
    
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can update team settings")
        
        updates = []
        params = []
        
        if update_data.name is not None:
            updates.append("name = %s")
            params.append(update_data.name)
        
        if update_data.description is not None:
            updates.append("description = %s")
            params.append(update_data.description)
        
        if update_data.settings is not None:
            updates.append("settings = %s::jsonb")
            params.append(json.dumps(update_data.settings))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.append(team_id)
        
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE teams SET {', '.join(updates)}, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, slug, description, owner_id, settings, created_at, updated_at""",
                tuple(params)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        return serialize_team(dict(zip(columns, row)))
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating team: {str(e)}")


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Delete a team (owner only)."""
    try:
        team = get_team_or_404(conn, team_id)
        
        if str(team['owner_id']) != user.id:
            raise HTTPException(status_code=403, detail="Only the team owner can delete the team")
        
        with conn.cursor() as cur:
            cur.execute("DELETE FROM teams WHERE id = %s", (team_id,))
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting team: {str(e)}")


# =============================================================================
# Team Members Endpoints
# =============================================================================

@router.get("/{team_id}/members", response_model=TeamMemberListResponse)
def list_team_members(
    team_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """List team members."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id,
                                     [TeamRole.OWNER, TeamRole.ADMINISTRATOR, TeamRole.MEMBER, TeamRole.GUEST]):
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        
        with conn.cursor() as cur:
            # E2E (TM-05/TM-06) や UI 表示で member.user_email を必要とするため、
            # users テーブルを LEFT JOIN して email/name を一緒に返す。
            cur.execute(
                """SELECT tm.id, tm.team_id, tm.user_id, tm.role, tm.notification_enabled,
                          tm.joined_at, tm.updated_at,
                          u.email AS user_email, u.name AS user_name
                   FROM team_members tm
                   LEFT JOIN users u ON u.id = tm.user_id
                   WHERE tm.team_id = %s
                   ORDER BY tm.joined_at""",
                (team_id,)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        members = []
        for row in rows:
            member = dict(zip(columns, row))
            members.append({
                "id": str(member['id']),
                "team_id": str(member['team_id']),
                "user_id": str(member['user_id']),
                "role": member['role'],
                "notification_enabled": member['notification_enabled'],
                "joined_at": member['joined_at'].isoformat() if member['joined_at'] else None,
                "updated_at": member['updated_at'].isoformat() if member['updated_at'] else None,
                "user_email": member.get('user_email'),
                "user_name": member.get('user_name'),
            })
        
        return {
            "members": members,
            "total": len(members),
            "team_id": team_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing members: {str(e)}")


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=201)
def add_team_member(
    team_id: str,
    member_data: TeamMemberAdd,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Add a member to the team."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can add members")
        
        with conn.cursor() as cur:
            # Check if already a member
            cur.execute(
                "SELECT id FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, member_data.user_id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="User is already a member of this team")
            
            # Add member
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role, notification_enabled)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, team_id, user_id, role, notification_enabled, joined_at, updated_at""",
                (team_id, member_data.user_id, member_data.role or 'member', 
                 member_data.notification_enabled if member_data.notification_enabled is not None else True)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        member = dict(zip(columns, row))
        return {
            "id": str(member['id']),
            "team_id": str(member['team_id']),
            "user_id": str(member['user_id']),
            "role": member['role'],
            "notification_enabled": member['notification_enabled'],
            "joined_at": member['joined_at'].isoformat() if member['joined_at'] else None,
            "updated_at": member['updated_at'].isoformat() if member['updated_at'] else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding member: {str(e)}")


@router.put("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
def update_team_member(
    team_id: str,
    user_id: str,
    update_data: TeamMemberUpdate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Update a team member's role or settings."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can update members")
        
        # Cannot change owner's role
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, user_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Member not found")
            if row[0] == 'owner' and update_data.role and update_data.role != TeamRole.OWNER:
                raise HTTPException(status_code=400, detail="Cannot change owner's role. Transfer ownership first.")
        
        updates = []
        params = []
        
        if update_data.role is not None:
            updates.append("role = %s")
            params.append(update_data.role.value)
        
        if update_data.notification_enabled is not None:
            updates.append("notification_enabled = %s")
            params.append(update_data.notification_enabled)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.extend([team_id, user_id])
        
        with conn.cursor() as cur:
            # list_team_members と同じく user_email / user_name を返して
            # クライアント側の state 更新で member.user_email が失われないようにする。
            cur.execute(
                f"""UPDATE team_members SET {', '.join(updates)}, updated_at = NOW()
                    WHERE team_id = %s AND user_id = %s
                    RETURNING id, team_id, user_id, role, notification_enabled, joined_at, updated_at""",
                tuple(params)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            member = dict(zip(columns, row))
            cur.execute(
                "SELECT email, name FROM users WHERE id = %s",
                (member['user_id'],)
            )
            user_row = cur.fetchone()

        conn.commit()

        return {
            "id": str(member['id']),
            "team_id": str(member['team_id']),
            "user_id": str(member['user_id']),
            "role": member['role'],
            "notification_enabled": member['notification_enabled'],
            "joined_at": member['joined_at'].isoformat() if member['joined_at'] else None,
            "updated_at": member['updated_at'].isoformat() if member['updated_at'] else None,
            "user_email": user_row[0] if user_row else None,
            "user_name": user_row[1] if user_row else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating member: {str(e)}")


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove_team_member(
    team_id: str,
    user_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Remove a member from the team."""
    try:
        get_team_or_404(conn, team_id)
        
        # User can remove themselves, or admin/owner can remove others
        is_self = user_id == user.id
        is_admin = check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR])
        
        if not is_self and not is_admin:
            raise HTTPException(status_code=403, detail="You don't have permission to remove this member")
        
        # Cannot remove owner
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, user_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Member not found")
            if row[0] == 'owner':
                raise HTTPException(status_code=400, detail="Cannot remove team owner. Transfer ownership first.")
            
            cur.execute(
                "DELETE FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, user_id)
            )
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing member: {str(e)}")


# =============================================================================
# Team Invitations Endpoints
# =============================================================================

@router.get("/{team_id}/invitations", response_model=TeamInvitationListResponse)
def list_team_invitations(
    team_id: str,
    status: Optional[InvitationStatus] = None,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """List team invitations."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can view invitations")
        
        query = """SELECT id, team_id, email, role, invited_by, message, token, status,
                          expires_at, accepted_at, created_at
                   FROM team_invitations
                   WHERE team_id = %s"""
        params = [team_id]
        
        if status:
            query += " AND status = %s"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        invitations = []
        for row in rows:
            inv = dict(zip(columns, row))
            invitations.append({
                "id": str(inv['id']),
                "team_id": str(inv['team_id']),
                "email": inv['email'],
                "role": inv['role'],
                "invited_by": str(inv['invited_by']),
                "message": inv['message'],
                "token": inv['token'],
                "status": inv['status'],
                "expires_at": inv['expires_at'].isoformat() if inv['expires_at'] else None,
                "accepted_at": inv['accepted_at'].isoformat() if inv['accepted_at'] else None,
                "created_at": inv['created_at'].isoformat() if inv['created_at'] else None,
            })
        
        return {
            "invitations": invitations,
            "total": len(invitations),
            "team_id": team_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing invitations: {str(e)}")


@router.post("/{team_id}/invitations", response_model=TeamInvitationResponse, status_code=201)
async def create_team_invitation(
    team_id: str,
    invitation_data: TeamInvitationCreate,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Create a new team invitation."""
    try:
        team = get_team_or_404(conn, team_id)

        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can create invitations")

        token = generate_invitation_token()
        expires_in_days = invitation_data.expires_in_days or 7
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        with conn.cursor() as cur:
            # Check for existing pending invitation
            cur.execute(
                """SELECT id FROM team_invitations
                   WHERE team_id = %s AND email = %s AND status = 'pending'""",
                (team_id, invitation_data.email)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="A pending invitation already exists for this email")

            cur.execute(
                """INSERT INTO team_invitations (team_id, email, role, invited_by, message, token, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id, team_id, email, role, invited_by, message, token, status, expires_at, created_at""",
                (team_id, invitation_data.email, invitation_data.role or 'member',
                 user.id, invitation_data.message, token, expires_at)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()

        conn.commit()

        inv = dict(zip(columns, row))

        # 招待メール送信（送信失敗は招待作成自体を失敗させない）
        try:
            from lib.auth.email_backends import get_email_backend
            from lib.auth.email_backends.templates import render_invitation_email

            accept_url = f"{settings.invitation_base_url}/accept-invitation?token={token}"
            inviter_name = user.name or user.email or "Unknown"
            subject, body = render_invitation_email(
                team_name=team['name'],
                inviter_name=inviter_name,
                accept_url=accept_url,
                expires_at=expires_at,
            )
            await get_email_backend().send(invitation_data.email, subject, body)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send invitation email: {e}")

        return {
            "id": str(inv['id']),
            "team_id": str(inv['team_id']),
            "email": inv['email'],
            "role": inv['role'],
            "invited_by": str(inv['invited_by']),
            "message": inv['message'],
            "token": inv['token'],
            "status": inv['status'],
            "expires_at": inv['expires_at'].isoformat() if inv['expires_at'] else None,
            "created_at": inv['created_at'].isoformat() if inv['created_at'] else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating invitation: {str(e)}")


@router.post("/invitations/accept", response_model=TeamMemberResponse)
def accept_team_invitation(
    accept_data: TeamInvitationAccept,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Accept a team invitation."""
    try:
        with conn.cursor() as cur:
            # Find invitation. FOR UPDATE で同一 token に対する並行受諾レースを直列化する
            # （auth.py の accept-invitation と同じパターン）。受諾時に token を NULL 化
            # するため、2 件目のリクエストは 1 件目の commit 後に READ COMMITTED の
            # WHERE 再評価でマッチする行が消え、`if not row` 分岐に落ちて 404 を返す
            # （UNIQUE 制約違反の 500 にはならない）。
            cur.execute(
                """SELECT id, team_id, email, role, status, expires_at
                   FROM team_invitations WHERE token = %s FOR UPDATE""",
                (accept_data.token,)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Invitation not found")
            
            inv_id, team_id, email, role, status, expires_at = row

            if status != 'pending':
                raise HTTPException(status_code=400, detail=f"Invitation is {status}")

            if expires_at:
                # psycopg2 が TIMESTAMPTZ を tz-aware で返すケースに合わせて
                # 比較対象も tz-aware にしておく。naive で来たら UTC 扱いに正規化。
                # auth.py の accept-invitation と同じパターン。
                now = datetime.now(timezone.utc)
                expires_at_aware = (
                    expires_at.replace(tzinfo=timezone.utc)
                    if expires_at.tzinfo is None
                    else expires_at
                )
                if expires_at_aware < now:
                    # Update status to expired and clear token (#55: replay prevention)
                    cur.execute(
                        "UPDATE team_invitations SET status = 'expired', token = NULL WHERE id = %s",
                        (inv_id,)
                    )
                    conn.commit()
                    raise HTTPException(status_code=400, detail="Invitation has expired")

            # Email 一致検証: invitation.email と user.email が一致しないと受諾不可
            if user.email and user.email.lower() != email.lower():
                raise HTTPException(status_code=403, detail="Invitation email does not match your account email")

            # Check if already a member
            cur.execute(
                "SELECT id FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, user.id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="You are already a member of this team")
            
            # Add as member
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, %s)
                   RETURNING id, team_id, user_id, role, notification_enabled, joined_at, updated_at""",
                (team_id, user.id, role)
            )
            columns = [desc[0] for desc in cur.description]
            member_row = cur.fetchone()
            
            # Update invitation status and clear token (#55: replay prevention)
            cur.execute(
                "UPDATE team_invitations SET status = 'accepted', accepted_at = NOW(), token = NULL WHERE id = %s",
                (inv_id,)
            )
        
        conn.commit()
        
        member = dict(zip(columns, member_row))
        return {
            "id": str(member['id']),
            "team_id": str(member['team_id']),
            "user_id": str(member['user_id']),
            "role": member['role'],
            "notification_enabled": member['notification_enabled'],
            "joined_at": member['joined_at'].isoformat() if member['joined_at'] else None,
            "updated_at": member['updated_at'].isoformat() if member['updated_at'] else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error accepting invitation: {str(e)}")


@router.delete("/{team_id}/invitations/{invitation_id}", status_code=204)
def cancel_team_invitation(
    team_id: str,
    invitation_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Cancel a pending invitation."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can cancel invitations")
        
        with conn.cursor() as cur:
            # token も NULL にしてキャンセル後の再利用を防ぐ (#55)
            cur.execute(
                """UPDATE team_invitations
                   SET status = 'cancelled', token = NULL
                   WHERE id = %s AND team_id = %s AND status = 'pending'
                   RETURNING id""",
                (invitation_id, team_id)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Pending invitation not found")
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling invitation: {str(e)}")


# =============================================================================
# Team Tilesets Endpoints
# =============================================================================

@router.get("/{team_id}/tilesets", response_model=TeamTilesetListResponse)
def list_team_tilesets(
    team_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """List tilesets shared with the team."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id,
                                     [TeamRole.OWNER, TeamRole.ADMINISTRATOR, TeamRole.MEMBER, TeamRole.GUEST]):
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        
        with conn.cursor() as cur:
            cur.execute(
                """SELECT tt.id, tt.team_id, tt.tileset_id, tt.added_by, tt.permission_level, tt.created_at,
                          t.name as tileset_name, t.type as tileset_type
                   FROM team_tilesets tt
                   JOIN tilesets t ON tt.tileset_id = t.id
                   WHERE tt.team_id = %s
                   ORDER BY tt.created_at DESC""",
                (team_id,)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        tilesets = []
        for row in rows:
            ts = dict(zip(columns, row))
            tilesets.append({
                "id": str(ts['id']),
                "team_id": str(ts['team_id']),
                "tileset_id": str(ts['tileset_id']),
                "added_by": str(ts['added_by']),
                "permission_level": ts['permission_level'],
                "created_at": ts['created_at'].isoformat() if ts['created_at'] else None,
                "tileset_name": ts['tileset_name'],
                "tileset_type": ts['tileset_type'],
            })
        
        return {
            "tilesets": tilesets,
            "total": len(tilesets),
            "team_id": team_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tilesets: {str(e)}")


@router.post("/{team_id}/tilesets", response_model=TeamTilesetResponse, status_code=201)
def add_team_tileset(
    team_id: str,
    tileset_data: TeamTilesetAdd,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Add a tileset to the team. Owner / administrator のみ実行可能。

    Issue #54 (案 B) で `remove_team_tileset` と権限を対称化。member の追加権限は
    廃止し、「owner/admin = 管理、member = 利用」の境界を統一。
    """
    try:
        get_team_or_404(conn, team_id)

        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="You don't have permission to add tilesets")
        
        with conn.cursor() as cur:
            # Check if already added
            cur.execute(
                "SELECT id FROM team_tilesets WHERE team_id = %s AND tileset_id = %s",
                (team_id, tileset_data.tileset_id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Tileset is already shared with this team")
            
            # Verify tileset exists
            cur.execute("SELECT id, name, type FROM tilesets WHERE id = %s", (tileset_data.tileset_id,))
            tileset = cur.fetchone()
            if not tileset:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            tileset_name, tileset_type = tileset[1], tileset[2]
            
            cur.execute(
                """INSERT INTO team_tilesets (team_id, tileset_id, added_by, permission_level)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, team_id, tileset_id, added_by, permission_level, created_at""",
                (team_id, tileset_data.tileset_id, user.id, tileset_data.permission_level or 'read')
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        ts = dict(zip(columns, row))
        return {
            "id": str(ts['id']),
            "team_id": str(ts['team_id']),
            "tileset_id": str(ts['tileset_id']),
            "added_by": str(ts['added_by']),
            "permission_level": ts['permission_level'],
            "created_at": ts['created_at'].isoformat() if ts['created_at'] else None,
            "tileset_name": tileset_name,
            "tileset_type": tileset_type,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding tileset: {str(e)}")


@router.delete("/{team_id}/tilesets/{tileset_id}", status_code=204)
def remove_team_tileset(
    team_id: str,
    tileset_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Remove a tileset from the team."""
    try:
        get_team_or_404(conn, team_id)
        
        if not check_team_permission(conn, team_id, user.id, [TeamRole.OWNER, TeamRole.ADMINISTRATOR]):
            raise HTTPException(status_code=403, detail="Only owners and administrators can remove tilesets")
        
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM team_tilesets WHERE team_id = %s AND tileset_id = %s RETURNING id",
                (team_id, tileset_id)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tileset not found in team")
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing tileset: {str(e)}")


# =============================================================================
# Team Ownership Transfer
# =============================================================================

@router.post("/{team_id}/transfer-ownership", response_model=TeamResponse)
def transfer_team_ownership(
    team_id: str,
    transfer_data: TeamOwnershipTransfer,
    conn=Depends(get_connection),
    user: User = Depends(require_auth)
):
    """Transfer team ownership to another member."""
    try:
        team = get_team_or_404(conn, team_id)
        
        if str(team['owner_id']) != user.id:
            raise HTTPException(status_code=403, detail="Only the team owner can transfer ownership")
        
        new_owner_id = transfer_data.new_owner_id
        
        with conn.cursor() as cur:
            # Verify new owner is a member
            cur.execute(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, new_owner_id)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="New owner must be a team member")
            
            # Update team owner
            cur.execute(
                "UPDATE teams SET owner_id = %s, updated_at = NOW() WHERE id = %s",
                (new_owner_id, team_id)
            )
            
            # Update member roles
            cur.execute(
                "UPDATE team_members SET role = 'administrator' WHERE team_id = %s AND user_id = %s",
                (team_id, user.id)
            )
            cur.execute(
                "UPDATE team_members SET role = 'owner' WHERE team_id = %s AND user_id = %s",
                (team_id, new_owner_id)
            )
            
            # Return updated team
            cur.execute(
                """SELECT id, name, slug, description, owner_id, settings, created_at, updated_at
                   FROM teams WHERE id = %s""",
                (team_id,)
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        
        conn.commit()
        
        return serialize_team(dict(zip(columns, row)))
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error transferring ownership: {str(e)}")
