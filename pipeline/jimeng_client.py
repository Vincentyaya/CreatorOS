"""即梦视频生成客户端:火山引擎 OpenAPI v4 签名 + 异步任务轮询。

即梦视频3.0 Pro 支持:
- 文生视频(prompt → video)
- 图生视频(image + prompt → video,图作为首帧)

注意:本接口产出**纯画面无声**视频(Body/返回都无音频字段)。
需要带配音/音效的成片请用 xiaoyunque_client(小云雀 Seedance 2.0)。

签名/调用/错误解析复用 volc_base(与小云雀共用 cv 服务)。
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Literal, Optional

from .config import JIMENG_POLL_INTERVAL, require_jimeng_credentials
from . import volc_base

_ACCESS_DENIED_HINT = (
    "\n提示:该账号未授权调用即梦视频3.0 Pro。请在火山引擎控制台"
    "开通该服务,并确认 AK/SK 对应账号有 cv:CVSync2AsyncSubmitTask 权限。"
)


class JiMengClient:
    """即梦视频生成客户端,封装提交任务 + 轮询结果。"""

    def __init__(self):
        ak, sk = require_jimeng_credentials()
        self._service = volc_base.make_service(ak, sk)

    def submit_text_to_video(
        self,
        prompt: str,
        aspect_ratio: Literal[
            "16:9", "4:3", "1:1", "3:4", "9:16", "21:9"
        ] = "16:9",
        frames: Literal[121, 241] = 121,
        seed: int = -1,
    ) -> str:
        """提交文生视频任务,返回 task_id。

        Args:
            prompt: 提示词(中英文均可,建议 ≤400字,不超过800字)
            aspect_ratio: 视频长宽比
            frames: 帧数(121=5s, 241=10s)
            seed: 随机种子(-1=随机)
        """
        body = {
            "req_key": "jimeng_ti2v_v30_pro",
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "frames": frames,
            "seed": seed,
        }
        return self._submit(body)

    def submit_image_to_video(
        self,
        image_path: Path,
        prompt: str,
        frames: Literal[121, 241] = 121,
        seed: int = -1,
    ) -> str:
        """提交图生视频任务(图作为首帧),返回 task_id。

        图片会被自动裁剪到最接近的可选比例(["16:9","4:3","1:1","3:4","9:16","21:9"])。

        Args:
            image_path: 首帧图片路径(JPEG/PNG,<4.7MB,最大4096x4096,长短边比≤3)
            prompt: 提示词
            frames: 帧数(121=5s, 241=10s)
            seed: 随机种子(-1=随机)
        """
        data = image_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        body = {
            "req_key": "jimeng_ti2v_v30_pro",
            "binary_data_base64": [b64],
            "prompt": prompt,
            "frames": frames,
            "seed": seed,
        }
        return self._submit(body)

    def _call(self, action: str, body: dict) -> dict:
        return volc_base.call(self._service, action, body, "即梦")

    def _submit(self, body: dict) -> str:
        """内部:提交任务,返回 task_id。"""
        resp = self._call("CVSync2AsyncSubmitTask", body)
        code = resp.get("code")
        if code != 10000:
            raise RuntimeError(
                volc_base.format_error("即梦提交任务失败", resp, _ACCESS_DENIED_HINT)
            )
        return resp["data"]["task_id"]

    def poll_result(
        self,
        task_id: str,
        timeout: int = 300,
        interval: Optional[int] = None,
    ) -> str:
        """轮询任务结果,直到完成或超时,返回视频 URL(有效期1小时)。

        Args:
            task_id: 提交任务返回的 task_id
            timeout: 最大等待时间(秒)
            interval: 轮询间隔(秒),默认用 JIMENG_POLL_INTERVAL

        Raises:
            TimeoutError: 超时
            RuntimeError: 任务失败/未找到/过期
        """
        if interval is None:
            interval = JIMENG_POLL_INTERVAL
        body = {"req_key": "jimeng_ti2v_v30_pro", "task_id": task_id}
        start = time.time()

        while time.time() - start < timeout:
            resp = self._call("CVSync2AsyncGetResult", body)
            code = resp.get("code")
            status = resp.get("data", {}).get("status") if code == 10000 else None

            if code == 10000 and status == "done":
                video_url = resp["data"].get("video_url")
                if not video_url:
                    raise RuntimeError(
                        volc_base.format_error("任务完成但无结果(可能审核不通过)", resp)
                    )
                return video_url

            if status in ("not_found", "expired"):
                raise RuntimeError(f"任务 {task_id} 状态异常: {status}")

            if code != 10000:
                raise RuntimeError(volc_base.format_error("即梦查询失败", resp))

            # status in ("in_queue", "generating")
            time.sleep(interval)

        raise TimeoutError(f"任务 {task_id} 超时({timeout}s)")


def create_client() -> JiMengClient:
    """工厂函数:创建即梦客户端。"""
    return JiMengClient()
