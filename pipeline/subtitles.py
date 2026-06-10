"""阶段1:字幕获取。用 Qwen VL 转写视频语音,得到带时间轴的字幕。

复用 Qwen 的视频理解能力转写语音,零额外重型依赖。无语音的视频会返回空字幕。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .qwen_client import generate_json
from .models import Subtitles

_INSTRUCTION = """请转写这段视频里的语音/口播,输出带时间轴的字幕。
要求:
1. language:语音的语言(如 zh / en)。无任何语音时填 "none"。
2. segments:逐句切分,每句含 start(开始秒)、end(结束秒)、text(该句文字)。
3. full_text:全部文字拼接(句子间用空格)。
按视频实际语音如实转写,不要编造。若视频无人声,segments 留空、full_text 留空。"""


def transcribe(video_path: Path) -> Subtitles:
    """提取语音字幕。"""
    return generate_json(_INSTRUCTION, Subtitles, video_path=video_path)
