.team_id, tt.tileset_id, tt.added_by, tt.permission_level, tt.created_at, t.name as tileset_name, t.type as tileset_type
                   FROM team_tilesets tt JOIN tilesets t ON tt.tileset_id = t.id WHERE tt.team_id = %s ORDER BY tt.created_at DESC""",
                (team_id,)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        return {"tilesets": [serialize_team(dict(zip(columns, row))) for row in rows], "total": len(rows), "team_id": team_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing team tilesets: {str(e)}")


@router.delete("/{team_id}/tilesets/{tileset_id}", status_code=204)
def remove_tileset_from_team(team_id: str, tileset_id: str, conn=Depends(get_connection), user: User = Depends(require_auth)):
    try:
        role = require_team_role(conn, team_id, user, TeamRole.GUEST)
        with conn.cursor() as cur:
            cur.execute("SELECT added_by FROM team_tilesets WHERE team_id = %s AND tileset_id = %s", (team_id, tileset_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found in team")
            added_by = str(row[0])
            if added_by != user.id and not role.can_manage_team:
                raise HTTPException(status_code=403, detail="You don't have permission to remove this tileset")
            cur.execute("DELETE FROM team_tilesets WHERE team_id = %s AND tileset_id = %s", (team_id, tileset_id))
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing tileset: {str(e)}")


@router.post("/permissions/check", response_model=PermissionCheckResponse)
def check_permission(request: PermissionCheckRequest, conn=Depends(get_connection), user: User = Depends(require_auth)):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, is_public FROM tilesets WHERE id = %s", (request.tileset_id,))
            row = cur.fetchone()
            if not row:
                return {"allowed": False, "user_id": request.user_id, "tileset_id": request.tileset_id, "action": request.action, "reason": "Tileset not found"}
            owner_id, is_public = row
            if str(owner_id) == request.user_id:
                return {"allowed": True, "user_id": request.user_id, "tileset_id": request.tileset_id, "action": request.action, "permission_level": PermissionLevel.ADMIN, "reason": "User is the tileset owner"}
            if is_public and request.action == "read":
                return {"allowed": True, "user_id": request.user_id, "tileset_id": request.tileset_id, "action": request.action, "permission_level": PermissionLevel.READ, "reason": "Tileset is public"}
            cur.execute("SELECT tm.role, tt.permission_level FROM team_members tm JOIN team_tilesets tt ON tm.team_id = tt.team_id WHERE tm.user_id = %s AND tt.tileset_id = %s", (request.user_id, request.tileset_id))
            team_rows = cur.fetchall()
            if not team_rows:
                return {"allowed": False, "user_id": request.user_id, "tileset_id": request.tileset_id, "action": request.action, "reason": "No team-based access found"}
            highest_permission = None
            for team_role, override_perm in team_rows:
                perm = PermissionLevel(override_perm) if override_perm else PermissionLevel.from_role(TeamRole(team_role))
                if highest_permission is None or perm == PermissionLevel.ADMIN:
                    highest_permission = perm
                elif perm == PermissionLevel.WRITE and highest_permission == PermissionLevel.READ:
                    highest_permission = perm
        allowed = False
        if request.action == "read":
            allowed = highest_permission in (PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.ADMIN)
        elif request.action in ("create", "update"):
            allowed = highest_permission in (PermissionLevel.WRITE, PermissionLevel.ADMIN)
        elif request.action == "delete":
            allowed = highest_permission == PermissionLevel.ADMIN
        return {"allowed": allowed, "user_id": request.user_id, "tileset_id": request.tileset_id, "action": request.action, "permission_level": highest_permission, "reason": f"Team-based permission: {highest_permission.value if highest_permission else 'none'}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking permission: {str(e)}")


@router.post("/{team_id}/transfer-ownership", response_model=TeamResponse)
def transfer_ownership(team_id: str, transfer_data: TeamOwnershipTransfer, conn=Depends(get_connection), user: User = Depends(require_auth)):
    try:
        role = require_team_role(conn, team_id, user, TeamRole.OWNER)
        if role != TeamRole.OWNER:
            raise HTTPException(status_code=403, detail="Only the team owner can transfer ownership")
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM team_members WHERE team_id = %s AND user_id = %s", (team_id, transfer_data.new_owner_id))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="New owner must be an existing team member")
            cur.execute("UPDATE teams SET owner_id = %s, updated_at = NOW() WHERE id = %s", (transfer_data.new_owner_id, team_id))
            cur.execute("UPDATE team_members SET role = 'owner', updated_at = NOW() WHERE team_id = %s AND user_id = %s", (team_id, transfer_data.new_owner_id))
            cur.execute("UPDATE team_members SET role = 'administrator', updated_at = NOW() WHERE team_id = %s AND user_id = %s", (team_id, user.id))
            cur.execute(
                """SELECT t.id, t.name, t.slug, t.description, t.owner_id, t.settings, t.created_at, t.updated_at,
                          (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) as member_count,
                          (SELECT COUNT(*) FROM team_tilesets WHERE team_id = t.id) as tileset_count
                   FROM teams t WHERE t.id = %s""", (team_id,)
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
