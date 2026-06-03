"""Regression tests for the validation evidence note."""

from pathlib import Path


def test_validation_evidence_note_exists_and_is_linked() -> None:
    """Keep the evidence-ranking artifact discoverable from the repo root."""

    repo_root = Path(__file__).resolve().parents[1]
    note_path = repo_root / "docs" / "1215355507138772-validation-evidence.md"

    assert note_path.exists()

    note_text = note_path.read_text(encoding="utf-8")
    for required_text in (
        "existing user research",
        "support signals",
        "usage data",
        "stakeholder input",
        "Authoritative source for first-pass validation: none available yet.",
        "Highest-ranked available input: stakeholder / delivery intent",
        "Hypothesis: the product area is authenticated question answering over a user's own posts.",
        "60bdb96",
        "046b32d",
        "303d71a",
        "b0cf04d",
    ):
        assert required_text in note_text

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "docs/1215355507138772-validation-evidence.md" in readme_text
