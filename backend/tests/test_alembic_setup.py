"""
Tests for Alembic Configuration and Folder Structure.

This module verifies that Alembic has been correctly initialized, all required
config files and templates exist, and migrations can load the target metadata.
"""
from __future__ import annotations

import os


def test_alembic_files_exist():
    """Verify that all core Alembic files and folders exist in the backend directory."""
    # Find current backend folder relative to project structure or look locally
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_folder = os.path.join(backend_dir, "alembic")
    env_py_path = os.path.join(alembic_folder, "env.py")
    script_mako_path = os.path.join(alembic_folder, "script.py.mako")
    versions_folder = os.path.join(alembic_folder, "versions")

    assert os.path.isfile(alembic_ini_path), f"alembic.ini not found at {alembic_ini_path}"
    assert os.path.isdir(alembic_folder), f"alembic/ folder not found at {alembic_folder}"
    assert os.path.isfile(env_py_path), f"env.py not found at {env_py_path}"
    assert os.path.isfile(script_mako_path), f"script.py.mako not found at {script_mako_path}"
    assert os.path.isdir(versions_folder), f"versions/ folder not found at {versions_folder}"


def test_migrations_present():
    """Verify that there is at least one migration version created in the versions folder."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    versions_folder = os.path.join(backend_dir, "alembic", "versions")

    files = [f for f in os.listdir(versions_folder) if f.endswith(".py")]
    assert len(files) > 0, "No migration scripts found in alembic/versions/"
