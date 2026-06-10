"""阶段2:逆向 prompt。

用 Qwen VL 原生理解整段视频,反推出:整体风格、分镜、以及可复用的近似生成 prompt。
注意:这是"近似反推",得到的是风格相似的 prompt,而非原视频的真实生成 prompt。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .qwen_client import generate_json
from .models import ReversePrompt, Subtitles

_INSTRUCTION = """你是顶级的 AI 视频反推专家。请观看这段视频,逆向分析它是如何被生成的,\
输出可用于「复刻同款风格」的结构化结果。

要求:
1. summary:一句话概括视频内容与卖点。
2. style:整体视觉风格——色调、质感、光线、画质(如电影感/赛博朋克/小清新/3D渲染等)。
3. subject:核心主体(人物/物体/场景)。
4. mood:情绪氛围。
5. shots:逐个分镜拆解。每个分镜给出 timestamp(时间区间)、description(画面内容)、\
camera(运镜方式,如推拉摇移/固定/跟随)、visual_prompt(该分镜的英文近似生成 prompt,\
要具体到主体、动作、场景、风格、镜头、光线)。
6. overall_prompt:整条视频的综合英文 prompt,可直接喂给视频生成模型。
7. negative_hints:应避免出现的元素(英文)。

visual_prompt 和 overall_prompt 用英文(视频生成模型对英文支持更好),其余字段用中文。
"""


def reverse(
    video_path: Path,
    subtitles: Optional[Subtitles] = None,
) -> ReversePrompt:
    """逆向单个视频。可选传入字幕辅助叙事理解。"""
    prompt = _INSTRUCTION
    if subtitles and subtitles.full_text.strip():
        prompt += f"\n\n【视频字幕,辅助理解叙事】\n{subtitles.full_text}"

    return generate_json(prompt, ReversePrompt, video_path=video_path)
