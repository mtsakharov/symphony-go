"""Regression tests for the video-post v1 decision note."""

from pathlib import Path


def test_video_post_decision_note_exists_and_is_linked() -> None:
    """Keep the decision note discoverable from repo entry points."""

    repo_root = Path(__file__).resolve().parents[1]
    note_path = repo_root / "docs" / "video-post-v1-decision.md"

    assert note_path.exists()

    note_text = note_path.read_text(encoding="utf-8")
    for required_text in (
        "first-party mobile create-post flow",
        "video_post_transcode",
        "video-post-public",
        "max duration: 120 seconds",
        "Playback is allowed only in `ready`.",
    ):
        assert required_text in note_text

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "docs/video-post-v1-decision.md" in readme_text

    router_text = (repo_root / "src/app/api/v1/router.py").read_text(encoding="utf-8")
    assert "docs/video-post-v1-decision.md" in router_text
