"""ログイン試行カウントとレート制限判定。

email または IP の **どちらか** が閾値超過でロック。
"""

import os
from typing import Optional

from lib.config import get_settings

from .errors import RateLimited

MAX_FAILED_ATTEMPTS = 5
WINDOW_MINUTES = 15


def _e2e_bypass_enabled() -> bool:
    """E2E モードでレート制限をスキップしてよい状態か判定。

    fail-closed 設計: `E2E_MODE=1` **かつ** 非 production のときだけ True。
    production (settings.is_production) では E2E_MODE が誤って残っていても
    brute-force 防御を維持する。
    """
    if os.getenv("E2E_MODE") != "1":
        return False
    try:
        if get_settings().is_production:
            return False
    except Exception:
        # settings 取得に失敗するなら安全側に倒して制限を継続する。
        return False
    return True


def check_login_rate_limit(
    conn,
    *,
    email: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """直近 WINDOW_MINUTES 分間の失敗回数を確認し、閾値超過なら RateLimited を raise。

    `_e2e_bypass_enabled()` が True (= `E2E_MODE=1` かつ 非 production) の
    ときはレート制限をスキップする (issue #111)。E2E テストで意図的に wrong
    password を試すケース (AUTH-02) や、50+ テストが連続で login する fixture
    構成だと production 設定の閾値 (5 attempts / 15 min) で簡単に lock される
    ため。本番では `is_production` で fail-closed。
    """
    if _e2e_bypass_enabled():
        return

    if email is None and ip is None:
        return  # チェック対象なし

    email_lower = email.lower() if email else None

    with conn.cursor() as cur:
        # email チェック
        if email_lower is not None:
            cur.execute(
                """
                SELECT COUNT(*) FROM auth_login_attempts
                WHERE email = %s AND success = FALSE
                  AND attempted_at > NOW() - (%s || ' minutes')::INTERVAL
                """,
                (email_lower, WINDOW_MINUTES),
            )
            count = cur.fetchone()[0]
            if count >= MAX_FAILED_ATTEMPTS:
                raise RateLimited(
                    f"Too many failed attempts for this account. Retry in {WINDOW_MINUTES} minutes."
                )

        # IP チェック
        if ip is not None:
            cur.execute(
                """
                SELECT COUNT(*) FROM auth_login_attempts
                WHERE ip_address = %s AND success = FALSE
                  AND attempted_at > NOW() - (%s || ' minutes')::INTERVAL
                """,
                (ip, WINDOW_MINUTES),
            )
            count = cur.fetchone()[0]
            if count >= MAX_FAILED_ATTEMPTS:
                raise RateLimited(
                    f"Too many failed attempts from this IP. Retry in {WINDOW_MINUTES} minutes."
                )


def record_login_attempt(
    conn,
    *,
    email: str,
    success: bool,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """ログイン試行を記録。email は小文字正規化。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO auth_login_attempts (email, ip_address, success, user_agent)
            VALUES (%s, %s, %s, %s)
            """,
            (email.lower(), ip, success, user_agent),
        )
    conn.commit()


def cleanup_old_attempts(conn) -> int:
    """24 時間以上前の試行履歴を削除。Returns: 削除件数。"""
    with conn.cursor() as cur:
        cur.execute("SELECT cleanup_old_login_attempts()")
        count = cur.fetchone()[0]
    conn.commit()
    return count
