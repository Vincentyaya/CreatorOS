"""共享配置:环境变量、路径。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.getenv("CREATOROS_ENV_FILE") or Path(__file__).resolve().parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
CONFIG_DIR = ROOT / "config"

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.8-max")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

INLINE_VIDEO_MAX_MB = float(os.getenv("INLINE_VIDEO_MAX_MB", "20"))

AUTO_COMPRESS_OVER_MB = float(os.getenv("AUTO_COMPRESS_OVER_MB", "3"))
COMPRESS_WIDTH = int(os.getenv("COMPRESS_WIDTH", "720"))
COMPRESS_CRF = int(os.getenv("COMPRESS_CRF", "28"))


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "")

JIMENG_ACCESS_KEY_ID = os.getenv("JIMENG_ACCESS_KEY_ID", "")
JIMENG_SECRET_ACCESS_KEY = os.getenv("JIMENG_SECRET_ACCESS_KEY", "")
JIMENG_POLL_INTERVAL = int(os.getenv("JIMENG_POLL_INTERVAL", "10"))

XIAOYUNQUE_DURATION = os.getenv("XIAOYUNQUE_DURATION", "～30s")
XIAOYUNQUE_RATIO = os.getenv("XIAOYUNQUE_RATIO", "9:16")
XIAOYUNQUE_LANGUAGE = os.getenv("XIAOYUNQUE_LANGUAGE", "Chinese")
XIAOYUNQUE_WATERMARK = os.getenv("XIAOYUNQUE_WATERMARK", "true").lower() == "true"
XIAOYUNQUE_TIMEOUT = int(os.getenv("XIAOYUNQUE_TIMEOUT", "1200"))

WAN_VIDEO_API_KEY = os.getenv("WAN_VIDEO_API_KEY", "")
WAN_VIDEO_MODEL = os.getenv("WAN_VIDEO_MODEL", "wan3.0-video")
WAN_VIDEO_BASE_URL = os.getenv("WAN_VIDEO_BASE_URL", "")
WAN_VIDEO_RATIO = os.getenv("WAN_VIDEO_RATIO", "9:16")
WAN_VIDEO_RESOLUTION = os.getenv("WAN_VIDEO_RESOLUTION", "720P")
WAN_VIDEO_TIMEOUT = int(os.getenv("WAN_VIDEO_TIMEOUT", "900"))
WAN_VIDEO_POLL_INTERVAL = int(os.getenv("WAN_VIDEO_POLL_INTERVAL", "5"))
VIDEO_RENDER_STRATEGY = os.getenv("VIDEO_RENDER_STRATEGY", "provider").lower()

HAPPYHORSE_MODEL = os.getenv("HAPPYHORSE_MODEL", "happyhorse-1.1-r2v")
HAPPYHORSE_BASE_URL = os.getenv("HAPPYHORSE_BASE_URL", "")
HAPPYHORSE_RESOLUTION = os.getenv("HAPPYHORSE_RESOLUTION", "1080P")
HAPPYHORSE_TIMEOUT = int(os.getenv("HAPPYHORSE_TIMEOUT", "1200"))
HAPPYHORSE_POLL_INTERVAL = int(os.getenv("HAPPYHORSE_POLL_INTERVAL", "10"))

IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "") or WAN_VIDEO_API_KEY or QWEN_API_KEY
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "qwen-image-2.0")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "")
IMAGE_TIMEOUT = int(os.getenv("IMAGE_TIMEOUT", "180"))

DOUYIN_CLIENT_KEY = os.getenv("DOUYIN_CLIENT_KEY", "")
DOUYIN_CLIENT_SECRET = os.getenv("DOUYIN_CLIENT_SECRET", "")
DOUYIN_ACCESS_TOKEN = os.getenv("DOUYIN_ACCESS_TOKEN", "")
DOUYIN_HOT_API_URL = os.getenv(
    "DOUYIN_HOT_API_URL",
    "https://open.douyin.com/data/extern/billboard/hot_video/",
)
PLATFORM_HTTP_TIMEOUT = int(os.getenv("PLATFORM_HTTP_TIMEOUT", "15"))


def wan_video_key() -> str:
    return WAN_VIDEO_API_KEY or QWEN_API_KEY


def wan_video_base_url() -> str:
    if WAN_VIDEO_BASE_URL:
        return WAN_VIDEO_BASE_URL.rstrip("/")
    if "/compatible-mode/v1" in QWEN_BASE_URL:
        return QWEN_BASE_URL.split("/compatible-mode/v1")[0] + "/api/v1"
    return QWEN_BASE_URL.rstrip("/") + "/api/v1"


def image_base_url() -> str:
    return (IMAGE_BASE_URL or wan_video_base_url()).rstrip("/")


def happyhorse_base_url() -> str:
    if HAPPYHORSE_BASE_URL:
        return HAPPYHORSE_BASE_URL.rstrip("/")
    if "/compatible-mode/v1" in QWEN_BASE_URL:
        return QWEN_BASE_URL.split("/compatible-mode/v1")[0] + "/api/v1"
    return QWEN_BASE_URL.rstrip("/") + "/api/v1"


def require_qwen_key() -> str:
    if not QWEN_API_KEY:
        raise RuntimeError(
            "缺少 QWEN_API_KEY。请在 .env 中填入阿里云 DashScope API Key,"
            "或 export QWEN_API_KEY=..."
        )
    return QWEN_API_KEY


def require_gemini_key() -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "缺少 GEMINI_API_KEY。请复制 .env.example 为 .env 并填入 key,"
            "或 export GEMINI_API_KEY=..."
        )
    return GEMINI_API_KEY


def require_jimeng_credentials() -> tuple[str, str]:
    if not JIMENG_ACCESS_KEY_ID or not JIMENG_SECRET_ACCESS_KEY:
        raise RuntimeError(
            "缺少即梦凭据。请在 .env 中填入 JIMENG_ACCESS_KEY_ID "
            "和 JIMENG_SECRET_ACCESS_KEY"
        )
    return JIMENG_ACCESS_KEY_ID, JIMENG_SECRET_ACCESS_KEY
