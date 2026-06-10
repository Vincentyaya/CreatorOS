"""阶段5:视频生成 — 用小云雀生成带配音的成片视频。

小云雀 Seedance 2.0 直接出带配音/音效/口型对齐的成片,不是逐段分镜。
可选带参考视频(爆款复刻)或纯文本生成。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import requests

from .xiaoyunque_client import create_client
from .models import GeneratedVideo, GenerationResult, VideoPrompts


def generate_videos(
    prompts: VideoPrompts,
    output_dir: Path,
    ratio: str = "9:16",
    duration: str = "～30s",
    reference_video_url: Optional[str] = None,
    timeout: int = 1200,
) -> GenerationResult:
    """生成视频,返回汇总结果。

    小云雀模式:把所有 clip 的 prompt 拼成一个多镜头脚本,一次生成完整成片。

    Args:
        prompts: 阶段4输出的 VideoPrompts
        output_dir: 下载视频的目录
        ratio: 画幅 16:9/9:16/4:3/3:4
        duration: 时长 ～15s/～30s/40～60s
        reference_video_url: 参考视频公网URL(爆款复刻),留空则纯文本生成
        timeout: 轮询超时(秒),小云雀慢,默认1200s

    Returns:
        GenerationResult,包含生成状态和本地路径
    """
    client = create_client()
    result = GenerationResult()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 拼接多镜头脚本
    script_parts = []
    for clip in prompts.clips:
        script_parts.append(f"镜头{clip.index}: {clip.prompt}")
    full_script = "\n".join(script_parts)

    print(f"提交小云雀生成任务(ratio={ratio}, duration={duration})...")
    print(f"脚本:\n{full_script}\n")

    gen = GeneratedVideo(clip_index=0)  # 小云雀出一个完整视频,不分 clip
    try:
        # 提交任务
        video_url_list = [reference_video_url] if reference_video_url else None
        task_id = client.submit(
            prompt=full_script,
            video_url_list=video_url_list,
            ratio=ratio,
            duration=duration,
            enable_watermark=False,
        )
        gen.task_id = task_id
        gen.status = "generating"
        print(f"task_id={task_id}")

        # 轮询结果
        print("\n轮询生成结果(小云雀较慢,约需几分钟到十几分钟)...")
        poll_result = client.poll_result(task_id, timeout=timeout)
        gen.video_url = poll_result["video_url"]
        gen.status = "done"
        print(f"生成完成! resp_data={poll_result['resp_data']}")

        # 下载
        print("\n下载视频...")
        local_path = output_dir / "final_video.mp4"
        _download(gen.video_url, local_path)
        gen.local_path = str(local_path)
        print(f"下载完成: {local_path}")

    except Exception as e:  # noqa: BLE001
        gen.status = "failed"
        gen.error = str(e)
        print(f"失败: {e}")

    result.videos.append(gen)
    return result


def _download(url: str, dest: Path, chunk_size: int = 8192):
    """下载文件到本地。"""
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with dest.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)
