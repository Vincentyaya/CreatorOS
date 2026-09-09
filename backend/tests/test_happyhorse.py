from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.pipeline import video_generator as vg
from backend.pipeline.models import VideoPrompts, VideoPromptClip


def test_retry_recovers_provider_task_and_maps_roles(tmp_path, monkeypatch):
    reference = tmp_path / "role.png"
    reference.write_bytes(b"test-reference")
    client = Mock(model="happyhorse-1.1-r2v", resolution="1080P")
    client.submit.return_value = "existing-task"
    client.poll.side_effect = [TimeoutError("network timeout"), "https://example.com/video.mp4"]
    monkeypatch.setattr(vg, "HappyHorseClient", lambda: client)
    monkeypatch.setattr(vg, "_download", lambda url, target: target.write_bytes(b"video"))
    prompts = VideoPrompts(clips=[VideoPromptClip(index=1, duration_sec=15,
        prompt="Close-up", narration="今天下班了吗", on_screen_text="今天下班了吗")])
    args = dict(prompts=prompts, output_dir=tmp_path / "output", duration="15",
                reference_paths=[reference], characters=[{"name": "铁柱", "desc": "憨厚男声"}],
                scenes=[{"speaker": "铁柱", "emotion": "期待"}])
    assert vg.generate_videos(**args).videos[0].status == "failed"
    assert vg.generate_videos(**args).videos[0].status == "done"
    assert client.submit.call_count == 1
    prompt = client.submit.call_args.args[0]
    assert "[Image 1] 是铁柱" in prompt
    assert "0.0-15.0秒" in prompt
    assert "铁柱（期待）说" in prompt
    assert client.submit.call_args.kwargs["duration"] == 15


@pytest.mark.parametrize("value", ["30", "40～60s", "2", "nan"])
def test_reject_unsupported_duration(value):
    with pytest.raises(ValueError):
        vg._duration_seconds(value)
