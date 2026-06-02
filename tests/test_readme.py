"""README regression tests."""

from pathlib import Path

README_PATH = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_documents_current_workflow() -> None:
    """Keep the README aligned with the verified local workflow."""

    readme = README_PATH.read_text(encoding="utf-8")

    expected_commands = [
        "uv sync",
        "cp .env.example .env",
        "docker compose up -d postgres",
        "uv run alembic upgrade head",
        "uv run serve",
        "uv run ruff check .",
        "uv run mypy src tests",
        "uv run pytest",
        "uv run ruff format .",
        "make sync",
        "make run",
        "make lint",
        "make fmt",
        "make typecheck",
        "make test",
        "make migrate",
    ]

    for command in expected_commands:
        assert command in readme


def test_readme_omits_stale_or_sensitive_details() -> None:
    """Keep unsupported Docker guidance and credential-like strings out of the README."""

    readme = README_PATH.read_text(encoding="utf-8")

    unexpected_strings = [
        "docker compose up --build",
        "DATABASE_URL=",
        "postgresql+psycopg://",
        "POSTGRES_PASSWORD",
    ]

    for unexpected in unexpected_strings:
        assert unexpected not in readme
