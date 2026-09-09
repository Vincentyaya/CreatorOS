"""各阶段共享的数据模型。每个阶段的产物都用这些结构,落盘为 JSON。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 阶段1:字幕 ----------
class SubtitleSegment(BaseModel):
    start: float  # 秒
    end: float
    text: str


class Subtitles(BaseModel):
    language: str = "unknown"
    full_text: str = ""
    segments: List[SubtitleSegment] = Field(default_factory=list)


# ---------- 阶段2:逆向 prompt ----------
class Shot(BaseModel):
    """单个分镜的描述。"""
    index: int
    timestamp: str = ""          # 如 "00:03-00:07"
    description: str = ""        # 画面内容
    camera: str = ""             # 运镜
    visual_prompt: str = ""      # 该分镜的近似生成 prompt


class ReversePrompt(BaseModel):
    """逆向出的爆款视频画面/风格分析。"""
    summary: str = ""            # 整体一句话概括
    style: str = ""              # 整体视觉风格(色调/质感/光线)
    subject: str = ""            # 核心主体
    mood: str = ""               # 情绪氛围
    shots: List[Shot] = Field(default_factory=list)
    overall_prompt: str = ""     # 整条视频的综合近似 prompt
    negative_hints: str = ""     # 可能需要避免的元素


# ---------- 阶段3:仿写剧本 ----------
class ScriptScene(BaseModel):
    index: int
    duration_sec: float = 0.0
    visual: str = ""             # 画面描述
    narration: str = ""          # 口播/字幕文案
    on_screen_text: str = ""     # 屏幕文字
    speaker: str = ""
    emotion: str = ""


class Script(BaseModel):
    title: str = ""
    hook: str = ""               # 开头3秒钩子
    scenes: List[ScriptScene] = Field(default_factory=list)
    cta: str = ""                # 结尾引导
    caption: str = ""            # 发布文案
    hashtags: List[str] = Field(default_factory=list)


# ---------- 阶段4:新视频 prompt ----------
class VideoPromptClip(BaseModel):
    index: int
    duration_sec: float = 0.0
    prompt: str = ""             # 喂给视频生成模型的 prompt
    negative_prompt: str = ""
    narration: str = ""          # 对应口播,便于配音
    on_screen_text: str = ""


class VideoPrompts(BaseModel):
    target_model: str = "generic"  # 目标视频模型(可灵/即梦/runway...)
    clips: List[VideoPromptClip] = Field(default_factory=list)


# ---------- 阶段5:生成结果 ----------
class GeneratedVideo(BaseModel):
    """单条生成任务的结果。"""
    clip_index: int
    task_id: str = ""            # 即梦返回的 task_id
    status: str = "pending"      # pending/generating/done/failed
    video_url: str = ""          # 生成的视频 URL(有效期1小时)
    local_path: str = ""         # 下载到本地的路径
    error: str = ""              # 失败时的错误信息


class GenerationResult(BaseModel):
    """整个视频生成任务的汇总结果。"""
    videos: List[GeneratedVideo] = Field(default_factory=list)
