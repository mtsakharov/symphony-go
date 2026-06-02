"""README documentation tests."""

from __future__ import annotations

import re
from pathlib import Path

README_PATH = Path(__file__).resolve().parents[1] / "README.md"
REPO_ROOT = README_PATH.parent


def extract_section(markdown: str, heading: str) -> str:
    """Return the content for a level-two README section."""

    pattern = rf"^## {re.escape(heading)}\n\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, re.MULTILINE | re.DOTALL)
    assert match is not None, f"Missing README section: {heading}"
    return match.group("body")


def test_contributor_checks_documents_real_validation_commands() -> None:
    """Contributor checks should list the repo's canonical validation commands."""

    section = extract_section(README_PATH.read_text(encoding="utf-8"), "Contributor checks")

    assert "uv run ruff check ." in section
    assert "uv run mypy src tests" in section
    assert "uv run pytest" in section
    assert "uv run ruff format ." in section
    assert "make typecheck" not in section


def test_contributor_check_links_point_to_existing_repo_files() -> None:
    """README references in the contributor section should resolve in-repo."""

    section = extract_section(README_PATH.read_text(encoding="utf-8"), "Contributor checks")
    local_links = {
        link
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", section)
        if "://" not in link and not link.startswith("#")
    }

    assert {"Makefile", ".env.example"} <= local_links
    for link in local_links:
        assert (REPO_ROOT / link).is_file(), f"Missing linked file: {link}"
