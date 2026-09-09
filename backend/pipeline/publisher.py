"""发布包生成器:生成视频发布所需的所有素材。

导出视频文件+文案+话题标签,方便用户手动发布到抖音/小红书等平台。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from .models import Script


def generate_publish_package(
    video_path: Path,
    script: Script,
    output_dir: Path,
    platform: str = "douyin",
) -> dict:
    """生成发布包。

    Args:
        video_path: 生成的视频文件路径
        script: 仿写剧本(包含标题、文案、话题标签等)
        output_dir: 发布包输出目录
        platform: 目标平台(douyin/xiaohongshu)

    Returns:
        发布包元数据字典
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 复制视频到发布包
    video_dest = output_dir / "video.mp4"
    shutil.copy2(video_path, video_dest)
    print(f"视频已复制: {video_dest}")

    # 2. 生成文案
    caption = _generate_caption(script, platform)
    caption_file = output_dir / "caption.txt"
    caption_file.write_text(caption, encoding="utf-8")
    print(f"文案已保存: {caption_file}")

    # 3. 提取话题标签
    hashtags = _extract_hashtags(script, platform)
    hashtags_file = output_dir / "hashtags.txt"
    hashtags_file.write_text("\n".join(hashtags), encoding="utf-8")
    print(f"话题标签已保存: {hashtags_file}")

    # 4. 生成元数据JSON
    metadata = {
        "platform": platform,
        "title": script.title,
        "caption": caption,
        "hashtags": hashtags,
        "hook": script.hook,
        "video_file": "video.mp4",
        "scenes_count": len(script.scenes),
    }
    metadata_file = output_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"元数据已保存: {metadata_file}")

    # 5. 生成发布指南
    guide = _generate_publish_guide(metadata, platform)
    guide_file = output_dir / "发布指南.md"
    guide_file.write_text(guide, encoding="utf-8")
    print(f"发布指南已保存: {guide_file}")

    return metadata


def _generate_caption(script: Script, platform: str) -> str:
    """生成平台适配的文案。"""
    if script.caption:
        return script.caption
    parts = []

    # 标题/钩子
    if script.hook:
        parts.append(script.hook)
    elif script.title:
        parts.append(script.title)

    # 正文(从场景旁白提取)
    body_parts = []
    for scene in script.scenes[:3]:  # 取前3个场景的旁白
        if scene.narration:
            body_parts.append(scene.narration)

    if body_parts:
        parts.append("\n\n" + "\n".join(body_parts))

    # 话题标签
    hashtags = _extract_hashtags(script, platform)
    if hashtags:
        parts.append("\n\n" + " ".join(hashtags))

    return "\n".join(parts)


def _extract_hashtags(script: Script, platform: str) -> list[str]:
    """提取话题标签。"""
    if script.hashtags:
        return list(dict.fromkeys(f"#{tag.lstrip('#')}" for tag in script.hashtags))
    hashtags = []

    # 从标题提取关键词作为话题
    if script.title:
        # 简单规则:标题拆词+加#
        keywords = ["AI", "科普", "干货"]
        for kw in keywords:
            if kw in script.title:
                hashtags.append(f"#{kw}")

    # 平台特定话题
    if platform == "douyin":
        hashtags.extend(["#热门", "#推荐"])
    elif platform == "xiaohongshu":
        hashtags.extend(["#种草", "#好物推荐"])

    # 去重
    return list(dict.fromkeys(hashtags))


def _generate_publish_guide(metadata: dict, platform: str) -> str:
    """生成发布指南markdown。"""
    platform_name = {"douyin": "抖音", "xiaohongshu": "小红书"}.get(platform, platform)

    guide = f"""# {platform_name}发布指南

## 📹 视频文件
- 文件名: `{metadata['video_file']}`
- 场景数: {metadata['scenes_count']}

## 📝 文案
```
{metadata['caption']}
```

## 🏷️ 话题标签
{chr(10).join(f'- {tag}' for tag in metadata['hashtags'])}

## 📱 发布步骤

### {platform_name}
1. 打开{platform_name} App
2. 点击底部 "+" 号(发布按钮)
3. 选择 `video.mp4` 上传
4. 复制 `caption.txt` 中的文案,粘贴到文案框
5. 添加话题标签(从 `hashtags.txt` 复制)
6. 设置封面(可选)
7. 点击"发布"

## 💡 优化建议
- 发布时间: 早8-9点、中午12-13点、晚19-21点
- 封面选择: 选择画面清晰、人物表情丰富的帧
- 定位: 根据内容选择合适的地理位置标签
"""

    return guide
