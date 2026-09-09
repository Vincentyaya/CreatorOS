from __future__ import annotations

import base64
import io
import time
from pathlib import Path
import requests
from PIL import Image, ImageOps

from . import config


def _payload(response: requests.Response) -> dict:
    try:
        value = response.json()
        return value if isinstance(value, dict) else {}
    except ValueError as exc:
        raise RuntimeError(f"HappyHorse 返回非 JSON 响应（HTTP {response.status_code}）") from exc


class HappyHorseClient:
    """HappyHorse 1.1 R2V: upload references, submit, poll and download."""

    def __init__(self):
        self.key = config.require_qwen_key()
        self.model = config.HAPPYHORSE_MODEL
        self.resolution = config.HAPPYHORSE_RESOLUTION
        self.base = config.happyhorse_base_url()
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
            "X-DashScope-OssResourceResolve": "enable",
        }

    def upload_reference(self, path: Path) -> str:
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            source.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            source.save(output, "JPEG", quality=82, optimize=True)
        if output.tell() > 8 * 1024 * 1024:
            raise RuntimeError("角色参考图压缩后仍超过 8 MB")
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")

    def submit(self, prompt: str, references: list[Path], duration: int = 5) -> str:
        if not references:
            raise RuntimeError("HappyHorse R2V 至少需要一张角色参考图")
        urls = [self.upload_reference(path) for path in references[:9]]
        body = {
            "model": self.model,
            "input": {
                "prompt": prompt,
                "media": [{"type": "reference_image", "url": url} for url in urls],
            },
            "parameters": {"resolution": self.resolution, "ratio": "9:16", "duration": duration},
        }
        response = requests.post(
            self.base + "/services/aigc/video-generation/video-synthesis",
            headers=self.headers, json=body, timeout=60,
        )
        payload = _payload(response)
        output = payload.get("output") or {}
        task_id = output.get("task_id") or payload.get("task_id")
        if response.status_code != 200 or not task_id:
            raise RuntimeError(f"HappyHorse 任务提交失败：{payload.get('message') or payload.get('code') or response.status_code}")
        return task_id

    def poll(self, task_id: str) -> str:
        deadline = time.monotonic() + config.HAPPYHORSE_TIMEOUT
        while time.monotonic() < deadline:
            response = requests.get(self.base + "/tasks/" + task_id, headers={"Authorization": f"Bearer {self.key}"}, timeout=30)
            payload = _payload(response)
            output = payload.get("output") or {}
            status = output.get("task_status") or payload.get("task_status")
            if response.status_code != 200:
                raise RuntimeError(f"HappyHorse 任务查询失败：{payload.get('message') or response.status_code}")
            if status == "SUCCEEDED":
                url = output.get("video_url") or ((output.get("results") or [{}])[0].get("url"))
                if not url:
                    raise RuntimeError("HappyHorse 任务完成但未返回视频地址")
                return url
            if status in ("FAILED", "CANCELED"):
                raise RuntimeError(f"HappyHorse 生成失败：{output.get('message') or payload.get('message') or status}")
            time.sleep(config.HAPPYHORSE_POLL_INTERVAL)
        raise TimeoutError("HappyHorse 视频生成超时，可稍后从任务记录重试")
