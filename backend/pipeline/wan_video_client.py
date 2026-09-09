"""通义万相文本生视频客户端(DashScope 异步协议)。

替代小云雀:一次性提交多镜头 prompt,服务端轮询并下载成片。
默认模型 wan3.0-video 原生有声(台词/音效/BGM),最长 30 秒。
兼容旧协议模型(wan2.6/2.5/2.2/2.1,size 参数)。
"""
from __future__ import annotations

import time
from typing import Optional

import requests

from . import config

_LEGACY_PREFIXES = ("wan2.6", "wan2.5", "wan2.2", "wan2.1", "wanx")

_SIZES = {
    "16:9": {"720P": "1280*720", "1080P": "1920*1080"},
    "9:16": {"720P": "720*1280", "1080P": "1080*1920"},
    "1:1": {"720P": "960*960", "1080P": "1440*1440"},
    "4:3": {"720P": "1104*832", "1080P": "1648*1248"},
    "3:4": {"720P": "832*1104", "1080P": "1248*1648"},
}


def _headers():
    return {
        "Authorization": f"Bearer {config.wan_video_key()}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }


def _format_error(prefix: str, payload: dict) -> str:
    code = payload.get("code")
    message = payload.get("message") or payload.get("detail") or ""
    hint = "请确认已开通通义万相视频生成权限,并确保模型、Endpoint 与 API Key 属于同一地域。"
    if code == "InvalidParameter" and "not exist" in message.lower():
        hint = f"模型 {config.WAN_VIDEO_MODEL} 在当前业务空间不可用,请检查 WAN_VIDEO_MODEL 与 WAN_VIDEO_BASE_URL。"
    return f"{prefix}: code={code} message={message}\n{hint}"


class WanVideoClient:
    """通义万相生视频客户端,封装提交任务 + 轮询结果。"""

    def __init__(self):
        if not config.wan_video_key():
            raise RuntimeError("缺少 WAN_VIDEO_API_KEY(阿里云百炼/通义万相视频生成 Key)")
        self._model = config.WAN_VIDEO_MODEL
        self._base = config.wan_video_base_url()
        self._legacy = self._model.startswith(_LEGACY_PREFIXES)

    def submit(
        self,
        prompt: str,
        negative_prompt: str = "",
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        duration: int = 10,
        prompt_extend: bool = True,
        watermark: bool = False,
    ) -> str:
        """提交生视频任务,返回 task_id。"""
        ratio = ratio or config.WAN_VIDEO_RATIO
        resolution = resolution or config.WAN_VIDEO_RESOLUTION
        if self._legacy:
            parameters = {
                "size": _SIZES.get(ratio, {}).get(resolution, "720*1280"),
                "duration": duration,
                "prompt_extend": prompt_extend,
                "watermark": watermark,
            }
        else:
            parameters = {
                "resolution": resolution,
                "ratio": ratio,
                "duration": duration,
            }
        input_data: dict = {"prompt": prompt}
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        body = {
            "model": self._model,
            "input": input_data,
            "parameters": parameters,
        }
        url = f"{self._base}/services/aigc/video-generation/video-synthesis"
        resp = requests.post(url, headers=_headers(), json=body, timeout=60)
        data = _as_json(resp)
        if resp.status_code != 200 or not (data.get("output") or {}).get("task_id"):
            raise RuntimeError(_format_error("视频任务提交失败", data))
        return data["output"]["task_id"]

    def poll_result(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        interval: Optional[int] = None,
    ) -> dict:
        """轮询任务结果,返回 {video_url, task_status}。"""
        if timeout is None:
            timeout = config.WAN_VIDEO_TIMEOUT
        if interval is None:
            interval = config.WAN_VIDEO_POLL_INTERVAL
        url = f"{self._base}/tasks/{task_id}"
        start = time.time()

        while time.time() - start < timeout:
            resp = requests.get(url, headers=_headers(), timeout=30)
            data = _as_json(resp)
            if resp.status_code != 200:
                raise RuntimeError(_format_error("视频任务查询失败", data))

            output = data.get("output") or {}
            status = output.get("task_status") or data.get("code")
            if status == "SUCCEEDED":
                video_url = output.get("video_url")
                if not video_url:
                    raise RuntimeError("任务完成但未返回视频地址(可能审核未通过)")
                return {"video_url": video_url, "task_status": status}
            if status in ("FAILED", "CANCELED"):
                raise RuntimeError(_format_error("视频任务失败", output))
            # PENDING / RUNNING / SUSPENDED
            time.sleep(interval)

        raise TimeoutError(f"任务 {task_id} 超时({timeout}s)")


def _as_json(resp: requests.Response) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {"message": resp.text[:500]}