"""メールテンプレート。Phase 3 はプレーンテキストのみ。"""

from datetime import datetime
from typing import Optional, Tuple


def render_invitation_email(
    team_name: str,
    inviter_name: str,
    accept_url: str,
    expires_at: datetime,
) -> Tuple[str, str]:
    """招待メールの (subject, body) を返す。"""
    subject = f"[geo-base] チーム「{team_name}」への招待"
    body = (
        f"{inviter_name} さんから「{team_name}」への参加招待が届いています。\n"
        f"\n"
        f"以下のリンクをクリックしてアカウントを作成・参加してください:\n"
        f"{accept_url}\n"
        f"\n"
        f"このリンクは {expires_at.strftime('%Y-%m-%d %H:%M UTC')} まで有効です。\n"
        f"\n"
        f"-- \n"
        f"geo-base\n"
        f"このメールに心当たりがない場合は無視してください。\n"
    )
    return subject, body


def render_password_reset_email(
    user_name: Optional[str],
    reset_url: str,
    expires_at: datetime,
) -> Tuple[str, str]:
    """パスワードリセットメールの (subject, body) を返す。"""
    subject = "[geo-base] パスワードリセットのご案内"
    greeting = f"{user_name} さん" if user_name else "ユーザー"
    body = (
        f"{greeting}、\n"
        f"\n"
        f"アカウントのパスワードリセットが要求されました。\n"
        f"以下のリンクをクリックして新しいパスワードを設定してください:\n"
        f"{reset_url}\n"
        f"\n"
        f"このリンクは {expires_at.strftime('%Y-%m-%d %H:%M UTC')} まで有効です。\n"
        f"\n"
        f"心当たりがない場合は、このメールを無視してください。\n"
        f"アカウントは安全です。\n"
        f"\n"
        f"-- \n"
        f"geo-base\n"
    )
    return subject, body
