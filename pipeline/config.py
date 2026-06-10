"""共享配置:环境变量、路径。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
CONFIG_DIR = ROOT / "config"

# 模型配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
# 中转/自定义网关地址(如 wolfai)。留空则用 Google 官方。
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "")

# Qwen 模型配置(用于逆向 prompt)
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-vl-max-latest")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
# 单次内联视频的大小上限(MB)。中转一般只代理 generateContent,
# 不支持 Files API 上传,故默认走内联 base64。
INLINE_VIDEO_MAX_MB = float(os.getenv("INLINE_VIDEO_MAX_MB", "20"))

# 自动压缩:视频超过该大小(MB)就先用 ffmpeg 压缩再发送。
# 实测 wolfai 中转对含视频大请求有体积瓶颈,压到 1-2MB 最稳。
AUTO_COMPRESS_OVER_MB = float(os.getenv("AUTO_COMPRESS_OVER_MB", "3"))
# 压缩目标:画面宽度(高度按比例)和 CRF(越大越糊、文件越小)。
COMPRESS_WIDTH = int(os.getenv("COMPRESS_WIDTH", "720"))
COMPRESS_CRF = int(os.getenv("COMPRESS_CRF", "28"))

# 即梦视频生成(火山引擎)
JIMENG_ACCESS_KEY_ID = os.getenv("JIMENG_ACCESS_KEY_ID", "")
JIMENG_SECRET_ACCESS_KEY = os.getenv("JIMENG_SECRET_ACCESS_KEY", "")
JIMENG_POLL_INTERVAL = int(os.getenv("JIMENG_POLL_INTERVAL", "10"))

# 小云雀智能生视频 Agent 2.0(Seedance 2.0,自带配音/音效/口型对齐,一键出成片)
# 复用同一套火山引擎 AK/SK(cv 服务),但是独立服务、需单独开通。
XIAOYUNQUE_DURATION = os.getenv("XIAOYUNQUE_DURATION", "～30s")  # ～15s/～30s/40～60s
XIAOYUNQUE_RATIO = os.getenv("XIAOYUNQUE_RATIO", "9:16")        # 16:9/9:16/4:3/3:4
XIAOYUNQUE_LANGUAGE = os.getenv("XIAOYUNQUE_LANGUAGE", "Chinese")
# 是否打明水印(左上"AI生成"、右下"小云雀AI生成")。发布场景一般想去掉。
XIAOYUNQUE_WATERMARK = os.getenv("XIAOYUNQUE_WATERMARK", "false").lower() == "true"
# 小云雀生成慢(60s视频约10分钟),轮询超时单独放大。
XIAOYUNQUE_TIMEOUT = int(os.getenv("XIAOYUNQUE_TIMEOUT", "1200"))


def require_gemini_key() -> str:
    """需要 Gemini key 的阶段调用,缺失时给出清晰报错。"""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "缺少 GEMINI_API_KEY。请复制 .env.example 为 .env 并填入 key,"
            "或 export GEMINI_API_KEY=..."
        )
    return GEMINI_API_KEY


def require_qwen_key() -> str:
    """需要 Qwen key 的阶段调用,缺失时给出清晰报错。"""
    if not QWEN_API_KEY:
        raise RuntimeError(
            "缺少 QWEN_API_KEY。请在 .env 中填入阿里云 DashScope API Key,"
            "或 export QWEN_API_KEY=..."
        )
    return QWEN_API_KEY


def require_jimeng_credentials() -> tuple[str, str]:
    """需要即梦凭据的阶段调用,缺失时给出清晰报错。"""
    if not JIMENG_ACCESS_KEY_ID or not JIMENG_SECRET_ACCESS_KEY:
        raise RuntimeError(
            "缺少即梦凭据。请在 .env 中填入 JIMENG_ACCESS_KEY_ID "
            "和 JIMENG_SECRET_ACCESS_KEY"
        )
    return JIMENG_ACCESS_KEY_ID, JIMENG_SECRET_ACCESS_KEY
