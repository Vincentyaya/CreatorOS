"""阶段4:生成新视频 prompt。

融合「仿写剧本(新内容)」+「逆向风格(爆款的视觉调性)」,
为每个分镜产出可直接喂给视频生成模型的 prompt。
"""
from __future__ import annotations

from .qwen_client import generate_json
from .models import ReversePrompt, Script, VideoPrompts


def build(
    script: Script,
    reverse: ReversePrompt,
    target_model: str = "generic",
) -> VideoPrompts:
    """把仿写剧本的每个 scene 转成视频生成 prompt,沿用爆款的视觉风格。"""
    scenes_text = "\n".join(
        f"- 分镜{s.index}({s.duration_sec}s): 画面[{s.visual}] "
        f"口播[{s.narration}] 字幕[{s.on_screen_text}]"
        for s in script.scenes
    )

    prompt = f"""你是 AI 视频生成 prompt 工程师。请把下面的仿写剧本,\
转成逐分镜的视频生成 prompt,目标模型: {target_model}。

【要复用的视觉风格(来自爆款逆向)】
style: {reverse.style}
mood: {reverse.mood}
overall_prompt: {reverse.overall_prompt}
negative_hints: {reverse.negative_hints}

【仿写剧本分镜】
{scenes_text}

要求,为每个分镜输出一个 clip:
1. index、duration_sec 与剧本分镜对应。
2. prompt:英文,具体描述 主体+动作+场景+镜头运动+光线,并融入上面的视觉风格,\
保证各分镜风格统一连贯。
3. negative_prompt:英文,结合 negative_hints。
4. narration:对应口播(中文,便于后续配音)。
5. on_screen_text:屏幕字幕(中文)。

prompt 和 negative_prompt 用英文,narration 和 on_screen_text 用中文。"""

    result = generate_json(prompt, VideoPrompts)
    result.target_model = target_model
    return result
