"""Tests for auth CLI."""
import subprocess
import os
import pytest


class TestCli:
    def test_help_runs(self):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "--help"],
            cwd="/Users/otsuka/ws/projects/geofirm/geo-base/api",
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        assert "create-admin" in result.stdout

    def test_list_users_empty(self, db_conn, clean_auth_tables):
        env = os.environ.copy()
        env.update({
            "AUTH_PROVIDER": "local",
            "JWT_SECRET": "x" * 64,
            "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:15432/geo_base",
        })
        result = subprocess.run(
            ["uv", "run", "python", "-m", "lib.auth.cli", "list-users", "--json"],
            cwd="/Users/otsuka/ws/projects/geofirm/geo-base/api",
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "[]" in result.stdout
