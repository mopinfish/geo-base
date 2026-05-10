"""auth CLI: python -m lib.auth.cli <command>

Commands:
- create-admin: Create initial admin user
- revoke-user-tokens: Revoke all refresh tokens for a user
- cleanup-expired: Cleanup expired tokens and old data
- reset-password: Trigger password reset for a user
- list-users: List all users
"""
import argparse
import asyncio
import getpass
import json
import sys

from .errors import UserAlreadyExists, WeakPassword


async def cmd_create_admin(args):
    from . import get_auth_provider
    provider = get_auth_provider()

    email = args.email
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Passwords do not match", file=sys.stderr)
        sys.exit(1)

    name = input("Name (optional): ").strip() or None

    try:
        user = await provider.create_user(
            email=email, password=password, name=name,
            email_verified=True,
            # `users.role` カラムに直接 'admin' を書く (issue #78)。
            # 旧 `app_metadata` のみだと JWT payload に role が乗らないので
            # 将来 admin 限定 endpoint を足した時に既存 admin が弾かれる。
            role="admin",
            app_metadata={"role": "admin"},
        )
    except UserAlreadyExists:
        print(f"User with email {email} already exists", file=sys.stderr)
        sys.exit(1)
    except WeakPassword as e:
        print(f"Weak password: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK Admin user created: {user.id}")
    print(f"   Email: {user.email}")


async def cmd_revoke_user_tokens(args):
    from lib.database import get_db_connection

    from .tokens import revoke_all_user_tokens

    with get_db_connection() as conn:
        count = revoke_all_user_tokens(conn, args.user_id, reason="admin_revocation")

    print(f"OK Revoked {count} refresh tokens for user {args.user_id}")


async def cmd_cleanup_expired(args):
    from lib.database import get_db_connection

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cleanup_expired_refresh_tokens()")
            rt = cur.fetchone()[0]
            cur.execute("SELECT cleanup_old_login_attempts()")
            la = cur.fetchone()[0]
            cur.execute("SELECT cleanup_expired_password_reset_tokens()")
            pr = cur.fetchone()[0]
            # expire_old_invitations comes from 05_teams_schema.sql
            cur.execute("SELECT expire_old_invitations()")
            inv = cur.fetchone()[0]
        conn.commit()

    print("OK Cleanup complete:")
    print(f"   Refresh tokens removed:        {rt}")
    print(f"   Login attempts removed:        {la}")
    print(f"   Password reset tokens removed: {pr}")
    print(f"   Invitations expired:           {inv}")


async def cmd_reset_password(args):
    from . import get_auth_provider
    await get_auth_provider().request_password_reset(args.email)
    print(f"OK Password reset email triggered for {args.email}")


async def cmd_list_users(args):
    from lib.database import get_db_connection

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, email, name, role, is_active,
                          email_verified_at, last_login_at, created_at
                   FROM users ORDER BY created_at DESC"""
            )
            rows = cur.fetchall()

    users = []
    for row in rows:
        users.append({
            "id": str(row[0]), "email": row[1], "name": row[2], "role": row[3],
            "is_active": row[4],
            "email_verified": row[5] is not None,
            "last_login_at": row[6].isoformat() if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
        })

    if args.json:
        print(json.dumps(users, indent=2, ensure_ascii=False))
    else:
        if not users:
            print("(no users)")
            return
        for u in users:
            verified = "OK" if u["email_verified"] else "NG"
            active = "OK" if u["is_active"] else "NG"
            print(f"{u['id']}  {u['email']:30s}  active={active} verified={verified}")


def main():
    parser = argparse.ArgumentParser(prog="lib.auth.cli", description="geo-base auth CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create-admin", help="Create initial admin user")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_create_admin)

    p = sub.add_parser("revoke-user-tokens", help="Revoke all refresh tokens for a user")
    p.add_argument("user_id")
    p.set_defaults(func=cmd_revoke_user_tokens)

    p = sub.add_parser("cleanup-expired", help="Cleanup expired tokens and old data")
    p.set_defaults(func=cmd_cleanup_expired)

    p = sub.add_parser("reset-password", help="Trigger password reset for a user")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_reset_password)

    p = sub.add_parser("list-users", help="List all users")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list_users)

    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
