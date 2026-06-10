"""Qwen 客户端封装:视频理解 + 结构化 JSON 输出。用于逆向 prompt 阶段。

使用阿里云 DashScope API(OpenAI 兼容格式)。
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .config import (
    AUTO_COMPRESS_OVER_MB,
    QWEN_BASE_URL,
    QWEN_MODEL,
    require_qwen_key,
)
from .media import compress_video

T = TypeVar("T", bound=BaseModel)

_client: Optional[OpenAI] = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=require_qwen_key(),
            base_url=QWEN_BASE_URL,
        )
    return _client


def load_video_base64(path: Path) -> str:
    """加载视频并返回 base64 编码字符串。

    流程:
    1. 超过 AUTO_COMPRESS_OVER_MB → 先用 ffmpeg 压缩。
    2. 读取视频文件并 base64 编码。
    """
    size_mb = path.stat().st_size / (1024 * 1024)

    tmp_compressed: Optional[Path] = None
    if size_mb > AUTO_COMPRESS_OVER_MB:
        tmp_compressed = compress_video(path)
        new_mb = tmp_compressed.stat().st_size / (1024 * 1024)
        print(f"  [自动压缩] {size_mb:.1f}MB → {new_mb:.1f}MB")
        path = tmp_compressed
        size_mb = new_mb

    try:
        video_data = path.read_bytes()
        return base64.b64encode(video_data).decode("utf-8")
    finally:
        if tmp_compressed is not None:
            tmp_compressed.unlink(missing_ok=True)


def generate_json(
    prompt: str,
    schema: Type[T],
    video_path: Optional[Path] = None,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> T:
    """调用 Qwen VL 模型,强制返回符合 schema 的 JSON,解析为 pydantic 对象。

    video_path: 视频文件路径,可选(纯文本阶段不传)。
    max_retries: 网络偶发连接重置时自动重试。
    """
    # 构建消息内容
    content = []

    # 如果有视频,添加视频数据
    if video_path is not None:
        video_b64 = load_video_base64(video_path)
        content.append({
            "type": "video_url",
            "video_url": {
                "url": f"data:video/mp4;base64,{video_b64}"
            }
        })

    # 添加文本提示
    content.append({
        "type": "text",
        "text": prompt + "\n\n请严格按照以下 JSON Schema 输出:\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    })

    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            resp = client().chat.completions.create(
                model=model or QWEN_MODEL,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            text = resp.choices[0].message.content
            if not text:
                raise RuntimeError("Qwen 返回空内容")

            # 解析 JSON
            data = json.loads(text)
            return schema.model_validate(data)

        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 退避重试

    raise RuntimeError(
        f"Qwen 调用失败(已重试 {max_retries} 次): {last_err}"
    ) from last_err
