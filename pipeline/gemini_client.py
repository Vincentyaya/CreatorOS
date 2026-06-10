"""Gemini 客户端封装:视频理解 + 结构化 JSON 输出。各阶段复用。

针对中转网关(如 wolfai)做了适配:
- 支持自定义 base_url(GEMINI_BASE_URL)。
- 视频默认走「内联 base64」直接塞进 generateContent 请求体,
  因为中转通常只代理 generateContent,不支持 Files API 的分片上传。
- 超过内联上限的大文件,兜底尝试 Files API(仅官方/支持该端点的中转可用)。
"""
from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path
from typing import Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from .config import (
    AUTO_COMPRESS_OVER_MB,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    INLINE_VIDEO_MAX_MB,
    require_gemini_key,
)
from .media import compress_video

T = TypeVar("T", bound=BaseModel)

_client: Optional[genai.Client] = None


def client() -> genai.Client:
    global _client
    if _client is None:
        http_options = None
        if GEMINI_BASE_URL:
            http_options = types.HttpOptions(base_url=GEMINI_BASE_URL)
        _client = genai.Client(
            api_key=require_gemini_key(),
            http_options=http_options,
        )
    return _client


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "video/mp4"


def load_video_part(path: Path):
    """把视频加载为可放进 contents 的 Part。

    流程:
    1. 超过 AUTO_COMPRESS_OVER_MB → 先用 ffmpeg 压缩(中转对大请求有体积瓶颈)。
    2. 压缩后仍在内联上限内 → 内联 base64(只依赖 generateContent,中转友好)。
    3. 实在太大 → 兜底走 Files API(中转可能不支持)。
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
        if size_mb <= INLINE_VIDEO_MAX_MB:
            data = path.read_bytes()
            return types.Part.from_bytes(data=data, mime_type=_guess_mime(path))
        # 压缩后仍超内联上限:兜底 Files API
        return _upload_via_files_api(path)
    finally:
        if tmp_compressed is not None:
            tmp_compressed.unlink(missing_ok=True)


def _upload_via_files_api(path: Path):
    """Files API 上传并等待 ACTIVE。中转通常不支持此端点。"""
    import shutil, tempfile
    # SDK 内部对文件名做 ASCII 编码,中文文件名会崩。临时复制为 ASCII 名。
    suffix = path.suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shutil.copy2(path, tmp_path)
    try:
        f = client().files.upload(file=str(tmp_path))
    except Exception as e:  # noqa: BLE001
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"视频 {path.name} 超过内联上限 {INLINE_VIDEO_MAX_MB}MB,"
            f"尝试 Files API 上传失败(中转可能不支持该端点): {e}\n"
            "建议:压缩/截取视频到内联上限以内,或调大 INLINE_VIDEO_MAX_MB。"
        ) from e
    tmp_path.unlink(missing_ok=True)
    while f.state.name == "PROCESSING":
        time.sleep(2)
        f = client().files.get(name=f.name)
    if f.state.name == "FAILED":
        raise RuntimeError(f"Gemini 处理视频失败: {path}")
    return f


def generate_json(
    prompt: str,
    schema: Type[T],
    video_part=None,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> T:
    """调用 Gemini,强制返回符合 schema 的 JSON,解析为 pydantic 对象。

    video_part: load_video_part 的返回值,可选(纯文本阶段不传)。
    max_retries: 网络/中转偶发连接重置时自动重试(视频请求体积大,易抖动)。
    """
    contents = []
    if video_part is not None:
        contents.append(video_part)
    contents.append(prompt)

    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            resp = client().models.generate_content(
                model=model or GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.7,
                ),
            )
            # SDK 在指定 response_schema 时会填充 .parsed
            if getattr(resp, "parsed", None) is not None:
                return resp.parsed  # type: ignore[return-value]
            # 兜底:手动解析文本
            return schema.model_validate(json.loads(resp.text))
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 退避重试
    raise RuntimeError(
        f"Gemini 调用失败(已重试 {max_retries} 次): {last_err}"
    ) from last_err
