from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe


WORKSPACE = Path(__file__).resolve().parents[2]


def _avatar_path(draft: dict) -> Path | None:
    for character in draft.get("characters") or []:
        value = character.get("img") or ""
        if value.startswith("/avatars/"):
            candidate = WORKSPACE / "frontend" / "public" / value.lstrip("/")
            if candidate.is_file():
                return candidate
    return None


def render(draft: dict, output_dir: Path, seconds: int = 10) -> Path:
    """Render a local preview video so the full demo workflow remains interactive."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "final_video.mp4"
    ffmpeg = shutil.which("ffmpeg") or get_ffmpeg_exe()
    avatar = _avatar_path(draft)
    if avatar:
        command = [
            ffmpeg, "-nostdin", "-y", "-loop", "1", "-i", str(avatar),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(seconds),
            "-vf", "scale=660:660:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=0xEEF2FF,fade=t=in:st=0:d=0.5,fade=t=out:st=9.5:d=0.5",
            "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(target),
        ]
    else:
        command = [
            ffmpeg, "-nostdin", "-y", "-f", "lavfi", "-i", f"color=c=0x4F46E5:s=720x1280:r=24:d={seconds}",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(seconds),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(target),
        ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0 or not target.is_file() or target.stat().st_size < 1024:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"演示视频生成失败：{result.stderr[-500:]}")
    return target
