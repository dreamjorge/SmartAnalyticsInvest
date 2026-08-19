import tomllib
from pathlib import Path

import smartanalyticsinvest

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_project_metadata():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == smartanalyticsinvest.__version__ == "0.1.1"


def test_release_metadata_points_to_mit_license_file():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    license_file = ROOT / project["license"]["file"]
    license_text = license_file.read_text(encoding="utf-8")

    assert project["authors"] == [{"name": "Jorge"}]
    assert "License :: OSI Approved :: MIT License" in project["classifiers"]
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 Jorge" in license_text


def test_changelog_documents_initial_release():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 0.1.0" in changelog
    assert "local CSV CLI" in changelog
    assert "optional Yahoo Finance adapter" in changelog
