"""Tests for auth.email_backends."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from lib.auth.email_backends import (
    EmailBackend,
    NullEmailBackend,
    ConsoleEmailBackend,
    SMTPEmailBackend,
)


class TestNullBackend:
    @pytest.mark.asyncio
    async def test_records_messages(self):
        b = NullEmailBackend()
        await b.send("a@b.com", "Subject", "Body")
        assert len(b.sent) == 1
        assert b.sent[0] == {"to": "a@b.com", "subject": "Subject", "body": "Body"}

    @pytest.mark.asyncio
    async def test_clear_resets(self):
        b = NullEmailBackend()
        await b.send("a@b.com", "S", "B")
        b.clear()
        assert b.sent == []


class TestConsoleBackend:
    @pytest.mark.asyncio
    async def test_writes_to_stdout(self, capsys):
        b = ConsoleEmailBackend()
        await b.send("a@b.com", "Hello", "Body content")
        captured = capsys.readouterr()
        assert "a@b.com" in captured.out
        assert "Hello" in captured.out
        assert "Body content" in captured.out


class TestSMTPBackend:
    @pytest.mark.asyncio
    async def test_calls_smtp(self):
        with patch("lib.auth.email_backends.smtp_backend.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            b = SMTPEmailBackend(
                host="smtp.example.com", port=587,
                username="user", password="pass",
                from_addr="no-reply@example.com", use_tls=True,
            )
            await b.send("to@example.com", "Hi", "Body")

            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user", "pass")
            mock_server.send_message.assert_called_once()


class TestABCEnforcement:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            EmailBackend()
