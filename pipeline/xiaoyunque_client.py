"""小云雀智能生视频 Agent 2.0 客户端(Seedance 2.0)。

和即梦最大的区别:
- 一个 prompt(可带参考图/参考视频 URL)直接出一条**带配音/音效/口型对齐的成片**,
  不是逐段5秒分镜。这才是"出成片"。
- 输入参考素材走**公网 URL**(img_url_list / video_url_list),不是 base64。
- req_key = pippit_iv2v_v20_cvtob_with_vinput(有参考版)。
- 生成慢:60秒视频约10分钟,轮询超时要拉长。

复用 volc_base 的签名/调用/错误解析(同一套 cv 服务 AK/SK)。
"""
from __future__ import annotations

import time
from typing import Literal, Optional

from .config import (
    JIMENG_ACCESS_KEY_ID,
    JIMENG_POLL_INTERVAL,
    JIMENG_SECRET_ACCESS_KEY,
    XIAOYUNQUE_DURATION,
    XIAOYUNQUE_LANGUAGE,
    XIAOYUNQUE_RATIO,
    XIAOYUNQUE_TIMEOUT,
    XIAOYUNQUE_WATERMARK,
)
from . import volc_base

_REQ_KEY = "pippit_iv2v_v20_cvtob_with_vinput"
_ACCESS_DENIED_HINT = (
    "\n提示:该账号未授权调用小云雀智能生视频Agent 2.0。请在火山引擎控制台"
    "开通【智能生视频Agent-Seedance 2.0 fast 720p 有参考】服务,"
    "并确认 AK/SK 对应账号有 cv 服务调用权限。"
)


def _require_credentials() -> tuple[str, str]:
    if not JIMENG_ACCESS_KEY_ID or not JIMENG_SECRET_ACCESS_KEY:
        raise RuntimeError(
            "缺少火山引擎凭据。请在 .env 中填入 JIMENG_ACCESS_KEY_ID "
            "和 JIMENG_SECRET_ACCESS_KEY(小云雀复用同一套 cv 服务凭据)"
        )
    return JIMENG_ACCESS_KEY_ID, JIMENG_SECRET_ACCESS_KEY


class XiaoYunQueClient:
    """小云雀生视频客户端,封装提交任务 + 轮询结果。"""

    def __init__(self):
        ak, sk = _require_credentials()
        self._service = volc_base.make_service(ak, sk)

    def submit(
        self,
        prompt: str,
        img_url_list: Optional[list[str]] = None,
        video_url_list: Optional[list[str]] = None,
        ratio: Optional[str] = None,
        duration: Optional[str] = None,
        language: Optional[str] = None,
        enable_watermark: Optional[bool] = None,
    ) -> str:
        """提交生视频任务,返回 task_id。

        Args:
            prompt: 提示词/脚本(中英文均可,≤2000字)。可写多镜头脚本。
            img_url_list: 参考图公网URL列表(单张≤20MB,≤4096x4096)
            video_url_list: 参考视频公网URL列表(单条≤3分钟/200MB)
            ratio: 画幅 16:9/9:16/4:3/3:4,默认取 config
            duration: 时长 ～15s/～30s/40～60s,默认取 config
            language: 配音语言,默认 Chinese
            enable_watermark: 是否打水印,默认取 config(默认 False)

        注意:img+video 总数 ≤ 50。按入参视频时长+输出视频时长计费。
        """
        body: dict = {
            "req_key": _REQ_KEY,
            "prompt": prompt,
            "ratio": ratio or XIAOYUNQUE_RATIO,
            "duration": duration or XIAOYUNQUE_DURATION,
            "language": language or XIAOYUNQUE_LANGUAGE,
            "enable_watermark": (
                XIAOYUNQUE_WATERMARK if enable_watermark is None else enable_watermark
            ),
        }
        if img_url_list:
            body["img_url_list"] = img_url_list
        if video_url_list:
            body["video_url_list"] = video_url_list

        resp = volc_base.call(self._service, "CVSync2AsyncSubmitTask", body, "小云雀")
        if resp.get("code") != 10000:
            msg = volc_base.format_error(
                "小云雀提交任务失败", resp, _ACCESS_DENIED_HINT
            )
            # 业务层 Access Denied(code=50400 等)说明服务未开通
            if "Access Denied" in str(resp.get("message", "")):
                msg += _ACCESS_DENIED_HINT
            raise RuntimeError(msg)
        return resp["data"]["task_id"]

    def poll_result(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        interval: Optional[int] = None,
    ) -> dict:
        """轮询任务结果,返回 {video_url, duration, input_video_duration}。

        Args:
            task_id: 提交返回的 task_id
            timeout: 最大等待秒数,默认取 config(小云雀慢,默认1200s)
            interval: 轮询间隔秒,默认取 JIMENG_POLL_INTERVAL

        Raises:
            TimeoutError / RuntimeError
        """
        if timeout is None:
            timeout = XIAOYUNQUE_TIMEOUT
        if interval is None:
            interval = JIMENG_POLL_INTERVAL
        body = {"req_key": _REQ_KEY, "task_id": task_id}
        start = time.time()

        while time.time() - start < timeout:
            resp = volc_base.call(self._service, "CVSync2AsyncGetResult", body, "小云雀")
            code = resp.get("code")
            status = resp.get("data", {}).get("status") if code == 10000 else None

            if code == 10000 and status == "done":
                data = resp["data"]
                video_url = data.get("video_url")
                if not video_url:
                    raise RuntimeError(
                        volc_base.format_error(
                            "任务完成但无结果(可能审核不通过)", resp
                        )
                    )
                return {
                    "video_url": video_url,
                    "resp_data": data.get("resp_data", ""),
                    "aigc_meta_tagged": data.get("aigc_meta_tagged", False),
                }

            if status in ("not_found", "expired"):
                raise RuntimeError(f"任务 {task_id} 状态异常: {status}")

            if code != 10000:
                raise RuntimeError(volc_base.format_error("小云雀查询失败", resp))

            # processing / in_queue / generating
            time.sleep(interval)

        raise TimeoutError(f"任务 {task_id} 超时({timeout}s)")


def create_client() -> XiaoYunQueClient:
    return XiaoYunQueClient()
