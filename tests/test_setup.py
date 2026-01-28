"""Verify project setup is working correctly."""


def test_imports() -> None:
    """Verify core dependencies can be imported."""
    import pyairtable

    assert pyairtable is not None


def test_project_structure(project_root, scripts_dir) -> None:
    """Verify expected project files exist."""
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / ".env.example").exists()
    assert (scripts_dir / "connection.py").exists()
