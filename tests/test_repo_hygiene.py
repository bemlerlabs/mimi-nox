from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def test_given_git_tracked_files_when_checked_then_local_artifacts_are_not_tracked():
    """
    GIVEN the repository index
    WHEN open-source hygiene is checked
    THEN dependencies and local database artifacts are not tracked.
    """
    tracked = _git_ls_files()
    forbidden = [
        path
        for path in tracked
        if "/node_modules/" in f"/{path}/"
        or re.search(r"\.(db|sqlite|sqlite3|db-wal|db-shm)$", path)
        or re.search(r"(^|/)=\d", path)
        or re.search(r"^docs/media/.*\.(mp4|webm|mov)$", path)
    ]
    assert forbidden == []


def test_given_license_metadata_when_checked_then_apache_2_is_consistent():
    """
    GIVEN public license files and package metadata
    WHEN license consistency is checked
    THEN Apache-2.0 is declared everywhere relevant.
    """
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Apache License" in license_text
    assert "Version 2.0" in license_text
    assert pyproject["project"]["license"]["text"] == "Apache-2.0"
    assert "Apache License 2.0" in readme
