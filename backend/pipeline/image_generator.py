from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import config


def _image_url(payload: dict) -> str:
    output = payload.get("output") or {}
    choices = output.get("choices") or []
    if choices:
        content = ((choices[0].get("message") or {}).get("content") or [])
        for item in content:
            if item.get("image"):
                return item["image"]
            if item.get("image_url"):
                value = item["image_url"]
                return value.get("url", "") if isinstance(value, dict) else value
    for item in output.get("results") or payload.get("data") or []:
        if item.get("url"):
            return item["url"]
    return ""


def generate_character(name: str, prompt: str, target: Path) -> dict:
    if not config.IMAGE_API_KEY:
        raise RuntimeError("角色生图服务尚未配置")
    full_prompt = (
        f"Create an original character portrait for {name}. {prompt}. "
        "Single clearly visible character, centered, expressive face, polished 3D animated film style, "
        "clean simple background, square profile image, no text, no logo, no watermark."
    )
    response = requests.post(
        config.image_base_url() + "/services/aigc/multimodal-generation/generation",
        headers={"Authorization": f"Bearer {config.IMAGE_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": config.IMAGE_MODEL,
            "input": {"messages": [{"role": "user", "content": [{"text": full_prompt}]}]},
            "parameters": {"prompt_extend": True, "watermark": False, "n": 1, "size": "1280*1280"},
        },
        timeout=config.IMAGE_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("角色生图服务返回了无法识别的结果") from exc
    if response.status_code != 200:
        raise RuntimeError(f"角色生图失败：{payload.get('message') or payload.get('code') or response.status_code}")
    url = _image_url(payload)
    if not url:
        raise RuntimeError("角色生图完成但没有返回图片")
    target.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("data:image/"):
        target.write_bytes(base64.b64decode(url.split(",", 1)[1]))
    else:
        host = urlparse(url).hostname or ""
        if not any(host == suffix or host.endswith("." + suffix) for suffix in ("aliyuncs.com", "alicdn.com")):
            raise RuntimeError("角色生图返回了不受信任的下载地址")
        image = requests.get(url, timeout=60)
        image.raise_for_status()
        if len(image.content) > 10 * 1024 * 1024:
            raise RuntimeError("角色图片超过 10 MB")
        target.write_bytes(image.content)
    if target.stat().st_size < 1024:
        raise RuntimeError("角色图片内容为空")
    return {"provider": "dashscope-image", "model": config.IMAGE_MODEL}
