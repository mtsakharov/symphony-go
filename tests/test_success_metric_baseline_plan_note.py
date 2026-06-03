"""Regression tests for the success-metric planning note."""

from pathlib import Path


def test_success_metric_note_exists_and_is_linked() -> None:
    """Keep the success-metric artifact discoverable from the repo root."""

    repo_root = Path(__file__).resolve().parents[1]
    note_path = repo_root / "docs" / "1215355419762800-success-metric-baseline-plan.md"

    assert note_path.exists()

    note_text = note_path.read_text(encoding="utf-8")
    for required_text in (
        "Status: provisional success metric and baseline plan for Issue `1215354560850994`",
        "Primary metric: grounded answer rate for authenticated post-question requests.",
        "authenticated `/api/v1/chat` requests",
        "No authoritative usage baseline exists yet.",
        "The current numeric baseline is therefore unavailable",
        "Capture the first 14 full days of authenticated traffic",
        "extend the window to 28 days",
        "Require >=95% request-response join coverage",
        (
            "Do not substitute request volume, sign-ins, or total chat sessions for the "
            "success metric."
        ),
        "60bdb96",
        "046b32d",
        "303d71a",
        "b0cf04d",
    ):
        assert required_text in note_text

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "docs/1215355419762800-success-metric-baseline-plan.md" in readme_text
