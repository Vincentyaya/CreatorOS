from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .pipeline.models import Script

PLATFORMS = ["抖音", "快手", "小红书", "B站", "视频号"]


class Profile(BaseModel):
    avatar: str | None = Field(default=None, max_length=1_500_000)
    name: str = Field(min_length=1, max_length=120)
    niche: str = Field(min_length=1, max_length=200)
    audience: str = Field(min_length=1, max_length=2000)
    valueProposition: str = Field(default="", max_length=2000)
    contentPreferences: str = Field(default="", max_length=4000)
    formats: list[str] = Field(min_length=1, max_length=4)
    tone: str = Field(max_length=100)
    duration: int = Field(ge=15, le=600)
    platforms: list[str] = Field(min_length=1, max_length=5)

    @field_validator("name", "niche", "audience")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("内容不能为空")
        return value.strip()

    @field_validator("platforms")
    @classmethod
    def valid_platforms(cls, value):
        if any(p not in PLATFORMS for p in value):
            raise ValueError("不支持的平台")
        return list(dict.fromkeys(value))


class AccountCharacter(BaseModel):
    id: int
    emoji: str = Field(default="", max_length=20)
    name: str = Field(min_length=1, max_length=100)
    meta: str = Field(default="", max_length=300)
    persona: str = Field(default="", max_length=4000)
    quirk: str = Field(default="", max_length=1000)
    accent: str = Field(default="", max_length=300)
    avatar: str | None = Field(default=None, max_length=1_500_000)
    avatarPrompt: str | None = Field(default=None, max_length=4000)


class Account(BaseModel):
    profile: Profile
    chars: list[AccountCharacter] = Field(min_length=1, max_length=30)
    interaction: str = Field(default="", max_length=4000)
    forbidden: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("chars")
    @classmethod
    def unique_roles(cls, value):
        if len({c.id for c in value}) != len(value) or any(not c.name.strip() for c in value):
            raise ValueError("角色 ID 必须唯一，名称不能为空")
        return value


class SelectedCharacter(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    source: Literal["library", "generated", "upload"]
    name: str = Field(min_length=1, max_length=100)
    desc: str = Field(default="", max_length=4000)
    emoji: str = Field(default="", max_length=20)
    accent: str = Field(default="", max_length=300)
    img: str | None = Field(default=None, max_length=1_500_000)


class AnalysisInput(BaseModel):
    mode: Literal["demo", "live"] = "live"
    url: str = Field(default="", max_length=2000)
    title: str = Field(default="", max_length=300)
    transcript: str = Field(default="", max_length=30000)
    uploadId: str | None = None
    catalogId: str | None = Field(default=None, max_length=120)


class GenerateInput(BaseModel):
    mode: Literal["demo", "live"] = "live"
    topic: str = Field(min_length=1, max_length=1000)
    characters: list[SelectedCharacter] = Field(min_length=1, max_length=10)
    analysisId: str | None = None


class AvatarInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=5, max_length=2000)

    @field_validator("name", "prompt")
    @classmethod
    def avatar_text_not_blank(cls, value):
        if not value.strip():
            raise ValueError("角色名称和形象描述不能为空")
        return value.strip()


class DraftUpdate(BaseModel):
    script: Script
    revision: int = Field(ge=1)


class QueueInput(BaseModel):
    platforms: list[str] = Field(min_length=1, max_length=5)

    @field_validator("platforms")
    @classmethod
    def valid_platforms(cls, value):
        if any(p not in PLATFORMS for p in value):
            raise ValueError("不支持的平台")
        return list(dict.fromkeys(value))


class TopicInput(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    topic: str = Field(min_length=1, max_length=300)
    angle: str = Field(min_length=1, max_length=2000)
    referenceId: str = Field(default="", max_length=200)
    status: Literal["待研究", "已拆解", "已生成", "已发布", "已复盘"] = "待研究"
    source: Literal["trend", "review"] = "trend"

    @field_validator("topic", "angle")
    @classmethod
    def topic_text_not_blank(cls, value):
        if not value.strip():
            raise ValueError("选题内容不能为空")
        return value.strip()


class TopicUpdate(BaseModel):
    status: Literal["待研究", "已拆解", "已生成", "已发布", "已复盘"]
