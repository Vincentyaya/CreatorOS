"""Generate a complete HappyHorse short with persistent provider task recovery."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import requests

from .happyhorse_client import HappyHorseClient
from .models import GeneratedVideo, GenerationResult, VideoPrompts


def generate_videos(prompts: VideoPrompts, output_dir: Path, ratio=None, duration=None,
                    reference_paths=None, timeout=None, characters=None, scenes=None) -> GenerationResult:
    client = HappyHorseClient()
    references = reference_paths or []
    characters = characters or []
    scenes = scenes or []
    seconds = _duration_seconds(duration)
    if not references or len(references) != len(characters):
        raise ValueError("每个角色都需要一张对应参考图，请先生成或上传角色图片")
    if ratio and ratio != "9:16":
        raise ValueError("当前内测版仅支持竖屏 9:16")
    if timeout is not None:
        raise ValueError("请通过 HAPPYHORSE_TIMEOUT 配置任务超时")
    mapping = "\n".join(
        f"[Image {i + 1}] 是{c['name']}。人设与声线：{c.get('desc', '')}"
        for i, c in enumerate(characters)
    )
    total = sum(max(float(c.duration_sec), 0.1) for c in prompts.clips)
    elapsed = 0.0
    parts = []
    for i, clip in enumerate(prompts.clips):
        end = elapsed + seconds * max(float(clip.duration_sec), 0.1) / total
        scene = scenes[i] if i < len(scenes) else {}
        parts.append(f"{elapsed:.1f}-{end:.1f}秒：{clip.prompt}\n"
                     f"{scene.get('speaker', '')}（{scene.get('emotion', '')}）说：{clip.narration}\n"
                     f"同步字幕：{clip.on_screen_text}")
        elapsed = end
    negative = "，".join(dict.fromkeys(c.negative_prompt for c in prompts.clips if c.negative_prompt))
    prompt = (f"生成{seconds}秒竖屏多镜头短剧，原生中文对白和同步口型。\n角色绑定：\n{mapping}\n"
              "所有镜头保持角色外貌、服装、声线及场景空间关系一致，不互换身份。\n"
              + "\n".join(parts) + "\n对白清晰自然，逐句说话，不抢话、不漏句、不串声。"
              "底部显示同步中文字幕，白字细黑描边，不遮挡脸。轻微环境音，无背景音乐。\n避免：" + negative)
    output_dir.mkdir(parents=True, exist_ok=True)
    record_path = output_dir / "provider-task.json"
    fingerprint = hashlib.sha256((prompt + client.model + client.resolution + "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() for p in references)).encode()).hexdigest()
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    gen = GeneratedVideo(clip_index=0)
    try:
        if record.get("fingerprint") != fingerprint or record.get("status") == "failed":
            task_id = client.submit(prompt, references, duration=seconds)
            record = {"task_id": task_id, "fingerprint": fingerprint, "status": "submitted",
                      "prompt": prompt, "model": client.model, "duration": seconds,
                      "resolution": client.resolution}
            _save(record_path, record)
        gen.task_id = record["task_id"]
        gen.video_url = client.poll(gen.task_id)
        target = output_dir / "final_video.mp4"
        _download(gen.video_url, target)
        gen.local_path = str(target)
        gen.status = "done"
        record["status"] = "done"
        _save(record_path, record)
    except Exception as exc:
        gen.status = "failed"
        gen.error = str(exc)
        # Only terminal provider failures allow a fresh paid submission on retry.
        if "HappyHorse 生成失败" in str(exc):
            record["status"] = "failed"
            _save(record_path, record)
    return GenerationResult(videos=[gen])


def _save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _duration_seconds(duration):
    match = re.fullmatch(r"[～~]?\s*(\d+(?:\.\d+)?)\s*s?", str(duration or "15"))
    if not match:
        raise ValueError("当前内测版支持 3–15 秒，请精简剧本后重试")
    value = math.ceil(float(match.group(1)))
    if not 3 <= value <= 15:
        raise ValueError("当前内测版支持 3–15 秒，请精简剧本后重试")
    return value


def _download(url, dest):
    temp = dest.with_suffix(".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with temp.open("wb") as output:
            for chunk in response.iter_content(65536):
                output.write(chunk)
    temp.replace(dest)
