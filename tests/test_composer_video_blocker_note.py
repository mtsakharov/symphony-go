"""Regression coverage for the composer-video blocker note."""

from pathlib import Path


def test_composer_video_blocker_note_is_linked_from_readme() -> None:
    """Keep the repo mismatch escalation visible to reviewers."""

    repo_root = Path(__file__).resolve().parents[1]
    note_path = repo_root / "docs" / "asana-1215294165742754-composer-video-blocker.md"

    assert note_path.exists()

    note_text = note_path.read_text(encoding="utf-8")
    for required_text in (
        "Status: blocked in this repository",
        "origin/codex/1215307235424375-video-upload-initiation",
        "origin/codex/1215294389170346-video-asset-processing",
        "origin/codex/1215304005873858-create-video-posts-only-from-completed-uploads",
        "show `uploading`, `processing`, `ready`, and `failed` states in the UI",
    ):
        assert required_text in note_text

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "docs/asana-1215294165742754-composer-video-blocker.md" in readme_text
