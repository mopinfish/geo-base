"""Tests for auth CLI."""
import subprocess
import os
from pathlib import Path

# api/tests/test_auth/test_cli.py → api/tests/test_auth → api/tests → api
API_DIR = Path(__file__).resolve().parents[2]


class TestCli:
    def test_help_runs(self):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "--help"],
            cwd=str(API_DIR),
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        assert "create-admin" in result.stdout

    def test_list_users_empty(self, db_conn, clean_auth_tables, test_database_url):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
            "DATABASE_URL": test_database_url,
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "list-users", "--json"],
            cwd=str(API_DIR),
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "[]" in result.stdout
