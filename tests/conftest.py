"""Shared test fixtures for airtable skill tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


# === Path Fixtures ===


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Path to the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def scripts_dir(project_root) -> Path:
    """Path to the airtable scripts directory."""
    return project_root / "skills" / "airtable" / "scripts"


# === CLI Script Runner Fixture ===


@pytest.fixture(scope="session")
def run_script(scripts_dir):
    """
    Fixture to run CLI scripts via subprocess.

    Returns a callable that runs a script and returns the CompletedProcess.

    Usage:
        result = run_script("connection.py", ["test"])
        assert result.returncode == 0

        result = run_script("records.py", ["list", "--base-id", "appXXX"], env=custom_env)
        assert "records" in result.stdout
    """

    def _run(
        script_name: str, args: list[str] | None = None, env: dict | None = None
    ):
        script_path = scripts_dir / script_name
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        # Use provided env or copy current environment
        run_env = env if env is not None else os.environ.copy()

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=run_env,
        )

    return _run


# === Environment Fixtures ===


@pytest.fixture
def env_without_token():
    """Environment dict with AIRTABLE_API_TOKEN removed."""
    env = os.environ.copy()
    env.pop("AIRTABLE_API_TOKEN", None)
    return env


@pytest.fixture
def env_with_test_token():
    """Environment dict with a test token set."""
    env = os.environ.copy()
    env["AIRTABLE_API_TOKEN"] = "test_token"
    return env
