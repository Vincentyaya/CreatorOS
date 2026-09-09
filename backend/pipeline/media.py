"""媒体处理工具:用 ffmpeg 压缩视频,降低发往中转的请求体积。

实测 wolfai 中转对含视频的大请求有体积瓶颈(21MB原片会卡死),
故大视频先压到 1-2MB 级别再内联发送,画质对 AI 理解足够。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

from .config import COMPRESS_CRF, COMPRESS_WIDTH


def has_ffmpeg() -> bool:
    try:
        return Path(shutil.which("ffmpeg") or get_ffmpeg_exe()).is_file()
    except RuntimeError:
        return False


def compress_video(src: Path) -> Path:
    """把视频压缩到临时文件,返回临时文件路径。

    降分辨率到 COMPRESS_WIDTH 宽、用 CRF 控制体积,音频降到 64k。
    调用方负责用完后删除返回的临时文件。
    """
    if not has_ffmpeg():
        raise RuntimeError(
            "未找到 ffmpeg,无法自动压缩。请安装 ffmpeg,"
            "或手动把视频压到 AUTO_COMPRESS_OVER_MB 以内。"
        )

    suffix = src.suffix or ".mp4"
    fd = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    out = Path(fd.name)
    fd.close()

    cmd = [
        shutil.which("ffmpeg") or get_ffmpeg_exe(), "-nostdin", "-protocol_whitelist", "file,pipe", "-i", str(src),
        "-vf", f"scale={COMPRESS_WIDTH}:-2",
        "-c:v", "libx264", "-crf", str(COMPRESS_CRF), "-preset", "fast",
        "-c:a", "aac", "-b:a", "64k",
        str(out), "-y",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        out.unlink(missing_ok=True)
        raise RuntimeError("视频压缩超时，请使用更短的视频")
    if result.returncode != 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(
            f"ffmpeg 压缩失败(返回码 {result.returncode}):\n"
            f"{result.stderr[-500:]}"
        )
    return out


def extract_keyframes(src: Path, output_dir: Path, max_frames: int = 5) -> list[Path]:
    """均匀抽取小尺寸关键帧，作为视频理解的可靠降级路径。"""
    if not has_ffmpeg():
        raise RuntimeError("未找到 ffmpeg，无法从视频提取关键帧。")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame-%02d.jpg"
    cmd = [
        shutil.which("ffmpeg") or get_ffmpeg_exe(), "-nostdin", "-y", "-i", str(src),
        "-vf", "fps=1/2,scale=960:-2", "-frames:v", str(max_frames),
        "-q:v", "3", str(pattern),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("关键帧提取超时，请使用更短的视频。") from exc
    if result.returncode != 0:
        raise RuntimeError(f"关键帧提取失败：{result.stderr[-500:]}")
    frames = sorted(output_dir.glob("frame-*.jpg"))
    if not frames:
        raise RuntimeError("未从视频中提取到可分析画面。")
    return frames
