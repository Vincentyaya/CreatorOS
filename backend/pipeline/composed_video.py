from __future__ import annotations

import base64
import shutil
import subprocess
import textwrap
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont, ImageOps


WORKSPACE = Path(__file__).resolve().parents[2]
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]
PALETTES = [(238, 242, 255), (255, 247, 237), (240, 253, 244), (254, 242, 242)]


def _font(size: int):
    path = next((path for path in FONT_CANDIDATES if path.is_file()), None)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def _character_image(character: dict, data_dir: Path, scratch: Path) -> Path | None:
    value = character.get("img") or ""
    if value.startswith("/avatars/"):
        candidate = WORKSPACE / "frontend" / "public" / value.lstrip("/")
        return candidate if candidate.is_file() else None
    if value.startswith("/api/uploads/"):
        identifier = value.rsplit("/", 1)[-1]
        return next(iter((data_dir / "uploads").glob(identifier + ".*")), None)
    if value.startswith("data:image/"):
        try:
            target = scratch / (character.get("id", "character") + ".png")
            target.write_bytes(base64.b64decode(value.split(",", 1)[1]))
            return target
        except (ValueError, OSError):
            return None
    return None


def character_reference_paths(draft: dict, data_dir: Path, scratch: Path) -> list[Path]:
    scratch.mkdir(parents=True, exist_ok=True)
    references = []
    for character in (draft.get("characters") or [])[:9]:
        path = _character_image(character, data_dir, scratch)
        if not path:
            raise RuntimeError(f"角色 {character.get('name', '')} 缺少参考图，请先生成或上传")
        references.append(path)
    return references


def _wrap(text: str, width: int = 16) -> str:
    return "\n".join(textwrap.wrap(text.strip(), width=width, break_long_words=True, replace_whitespace=False))


def _frame(scene: dict, character: dict, avatar: Path | None, target: Path, index: int):
    canvas = Image.new("RGB", (720, 1280), PALETTES[index % len(PALETTES)])
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((48, 56, 672, 1224), radius=28, fill=(255, 255, 255), outline=(220, 225, 235), width=2)
    if avatar:
        with Image.open(avatar) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            portrait = ImageOps.fit(source, (540, 540), method=Image.Resampling.LANCZOS)
            mask = Image.new("L", portrait.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, 539, 539), radius=34, fill=255)
            canvas.paste(portrait, (90, 135), mask)
    else:
        draw.rounded_rectangle((90, 135, 630, 675), radius=34, fill=(235, 238, 245))
        draw.text((360, 405), character.get("emoji") or "AI", font=_font(90), fill=(79, 70, 229), anchor="mm")
    name = scene.get("speaker") or character.get("name") or "角色"
    emotion = scene.get("emotion") or ""
    draw.text((90, 730), name + (f" · {emotion}" if emotion else ""), font=_font(34), fill=(79, 70, 229))
    dialogue = _wrap(scene.get("on_screen_text") or scene.get("narration") or "")
    draw.multiline_text((90, 800), dialogue, font=_font(42), fill=(15, 23, 42), spacing=18)
    draw.text((90, 1160), "CreatorOS · AI 原创内容", font=_font(20), fill=(100, 116, 139))
    canvas.save(target, quality=95)


def _voice(text: str, target: Path, index: int):
    say = shutil.which("say")
    if say:
        voice = "Tingting" if index % 2 == 0 else "Meijia"
        result = subprocess.run([say, "-v", voice, "-r", "185", "-o", str(target), text], capture_output=True, timeout=60)
        if result.returncode == 0 and target.is_file() and target.stat().st_size > 1024:
            return
    raise RuntimeError("本机中文配音服务不可用")


def render(draft: dict, output_dir: Path, data_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = output_dir / "compose"
    scratch.mkdir(exist_ok=True)
    ffmpeg = shutil.which("ffmpeg") or get_ffmpeg_exe()
    characters = draft.get("characters") or []
    scenes = (draft.get("script") or {}).get("scenes") or []
    if not scenes:
        raise RuntimeError("剧本没有可合成的分镜")
    segments = []
    for index, scene in enumerate(scenes):
        character = next((item for item in characters if item.get("name") == scene.get("speaker")), characters[index % len(characters)])
        frame = scratch / f"frame-{index:02d}.jpg"
        audio = scratch / f"voice-{index:02d}.aiff"
        segment = scratch / f"segment-{index:02d}.mp4"
        _frame(scene, character, _character_image(character, data_dir, scratch), frame, index)
        _voice(scene.get("narration") or scene.get("on_screen_text") or "", audio, index)
        command = [
            ffmpeg, "-nostdin", "-y", "-loop", "1", "-framerate", "24", "-i", str(frame), "-i", str(audio),
            "-filter_complex", "[1:a]apad=pad_dur=0.45[a]", "-map", "0:v", "-map", "[a]", "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(segment),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            raise RuntimeError(f"分镜合成失败：{result.stderr[-500:]}")
        segments.append(segment)
    concat = scratch / "concat.txt"
    concat.write_text("".join(f"file '{path.name}'\n" for path in segments), encoding="utf-8")
    target = output_dir / "final_video.mp4"
    result = subprocess.run(
        [ffmpeg, "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(target)],
        cwd=scratch, capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0 or not target.is_file() or target.stat().st_size < 1024:
        raise RuntimeError(f"成片拼接失败：{result.stderr[-500:]}")
    return target
