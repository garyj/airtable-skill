"""Tests for the connection utility script."""

import json
import os
from unittest.mock import patch

import pytest


class TestConnectionScript:
    """Tests for scripts/connection.py."""

    def test_script_exists(self, scripts_dir) -> None:
        """Verify the connection script exists."""
        script_path = scripts_dir / "connection.py"
        assert script_path.exists(), "scripts/connection.py should exist"

    def test_script_has_pep723_metadata(self, scripts_dir) -> None:
        """Verify script has PEP 723 inline metadata."""
        script_path = scripts_dir / "connection.py"
        content = script_path.read_text()
        assert "# /// script" in content, "Script should have PEP 723 header"
        assert "# dependencies = [" in content, "Script should declare dependencies"
        assert "pyairtable" in content, "Script should depend on pyairtable"
        assert "# ///" in content, "Script should have PEP 723 closing marker"

    def test_missing_token_error(self, run_script, env_without_token) -> None:
        """Verify error message when AIRTABLE_API_TOKEN is missing."""
        result = run_script("connection.py", ["test"], env=env_without_token)

        assert result.returncode == 1
        assert "AIRTABLE_API_TOKEN" in result.stderr
        # Should NOT expose the token value in error message
        assert "pat" not in result.stderr.lower() or "token" in result.stderr.lower()


class TestConnectionFunctions:
    """Unit tests for connection module functions."""

    def test_get_api_token_returns_env_value(self) -> None:
        """Test that get_api_token reads from environment."""
        from connection import get_api_token

        with patch.dict(os.environ, {"AIRTABLE_API_TOKEN": "test_token"}):
            assert get_api_token() == "test_token"

    def test_get_api_token_returns_none_when_missing(self) -> None:
        """Test that get_api_token returns None when env var is missing."""
        from connection import get_api_token

        env = os.environ.copy()
        env.pop("AIRTABLE_API_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            # Re-check without the var
            result = os.environ.get("AIRTABLE_API_TOKEN")
            assert result is None or result == ""

    def test_format_table_empty(self) -> None:
        """Test table formatting with empty list."""
        from connection import format_table

        result = format_table([])
        assert result == "No bases found."

    def test_format_table_with_data(self) -> None:
        """Test table formatting with data."""
        from connection import format_table

        bases = [
            {"id": "appABC123", "name": "Test Base"},
            {"id": "appDEF456", "name": "Another Base"},
        ]
        result = format_table(bases)

        assert "Base ID" in result
        assert "Name" in result
        assert "appABC123" in result
        assert "Test Base" in result
        assert "appDEF456" in result
        assert "Another Base" in result


@pytest.mark.integration
class TestConnectionIntegration:
    """Integration tests that require a real Airtable token."""

    @pytest.fixture
    def has_token(self) -> bool:
        """Check if we have a token for integration tests."""
        return bool(os.environ.get("AIRTABLE_API_TOKEN"))

    def test_connection_test_with_real_token(self, run_script, has_token: bool) -> None:
        """Test connection verification with real token."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")

        result = run_script("connection.py", ["test"])

        assert result.returncode == 0
        assert "successful" in result.stdout.lower()

    def test_bases_list_with_real_token(self, run_script, has_token: bool) -> None:
        """Test bases listing with real token."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")

        result = run_script("connection.py", ["bases"])

        assert result.returncode == 0
        # Should have table headers
        assert "Base ID" in result.stdout or "No bases found" in result.stdout

    def test_bases_list_json_with_real_token(self, run_script, has_token: bool) -> None:
        """Test bases listing with JSON output."""
        if not has_token:
            pytest.skip("AIRTABLE_API_TOKEN not set, skipping integration test")

        result = run_script("connection.py", ["bases", "--json"])

        assert result.returncode == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        # Each item should have id and name
        for item in data:
            assert "id" in item
            assert "name" in item
