"""Tests for auth.email_backends.templates."""

from datetime import datetime, timezone

from lib.auth.email_backends.templates import (
    render_invitation_email,
    render_password_reset_email,
)


class TestInvitationTemplate:
    def test_returns_subject_and_body(self):
        subject, body = render_invitation_email(
            team_name="Acme Team",
            inviter_name="Alice",
            accept_url="https://example.com/accept?token=abc",
            expires_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
        assert "Acme Team" in subject
        assert "Alice" in body
        assert "https://example.com/accept?token=abc" in body
        assert "2026" in body  # 期限日が含まれる


class TestPasswordResetTemplate:
    def test_returns_subject_and_body(self):
        subject, body = render_password_reset_email(
            user_name="Alice",
            reset_url="https://example.com/reset?token=xyz",
            expires_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert "password" in subject.lower() or "パスワード" in subject
        assert "https://example.com/reset?token=xyz" in body

    def test_handles_no_user_name(self):
        subject, body = render_password_reset_email(
            user_name=None,
            reset_url="https://example.com/reset?token=xyz",
            expires_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
        assert "https://example.com/reset?token=xyz" in body
