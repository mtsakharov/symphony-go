"""Regression tests for the problem-statement planning note."""

from pathlib import Path


def test_problem_statement_note_exists_and_is_linked() -> None:
    """Keep the framing artifact discoverable from the repo root."""

    repo_root = Path(__file__).resolve().parents[1]
    note_path = repo_root / "docs" / "1215355506805570-problem-statement.md"

    assert note_path.exists()

    note_text = note_path.read_text(encoding="utf-8")
    for required_text in (
        "Status: provisional framing for Issue `1215354560850994`",
        "Signed-in users who want to ask questions about posts they have already authored or can access",
        "The moment a signed-in user wants to ask a focused question about their own accessible posts",
        "The current repo activity shows active delivery motion before the user problem is locked.",
        "No higher-authority research, support, or usage artifact is attached yet",
        "coordination risk, not confirmed demand",
        "b0cf04d",
        "046b32d",
        "303d71a",
        "60bdb96",
    ):
        assert required_text in note_text

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "docs/1215355506805570-problem-statement.md" in readme_text
