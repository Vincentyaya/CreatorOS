"""视频下载器:支持抖音、小红书等平台的无水印视频下载。

优先使用 you-get,失败则回退到 videofetch。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def download_with_youget(
    url: str,
    output_path: Optional[Path] = None,
) -> Path:
    """使用 you-get 下载视频。

    Args:
        url: 视频URL
        output_path: 输出路径,留空则自动生成临时文件

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 下载失败
    """
    if output_path is None:
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix="video_download_"))
        work_dir = temp_dir
        output_filename = None
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = output_path.parent
        output_filename = output_path.stem

    # you-get 命令
    # -o: 输出目录
    # -O: 输出文件名(不含扩展名)
    cmd = ["you-get", "-o", str(work_dir)]
    if output_filename:
        cmd.extend(["-O", output_filename])
    cmd.append(url)

    print(f"下载视频 (you-get): {url}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        # 检查下载的文件
        downloaded_files = list(work_dir.glob("*.mp4"))
        if not downloaded_files:
            downloaded_files = list(work_dir.glob("*.m4v"))
            downloaded_files.extend(list(work_dir.glob("*.mov")))
            downloaded_files.extend(list(work_dir.glob("*.flv")))

        if downloaded_files:
            actual_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)

            if output_path and actual_file != output_path:
                # 确保是 mp4 格式
                if actual_file.suffix != ".mp4":
                    final_path = output_path.with_suffix(actual_file.suffix)
                else:
                    final_path = output_path
                actual_file.rename(final_path)
            else:
                final_path = actual_file

            print(f"下载完成: {final_path}")
            return final_path

        # 下载失败
        error_msg = f"you-get 下载失败\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        raise RuntimeError(error_msg)

    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"下载超时(300s): {url}") from e
    except Exception as e:
        raise RuntimeError(f"you-get 下载出错: {e}") from e


def download_with_videofetch(
    url: str,
    output_path: Optional[Path] = None,
    parser: str = "SnapAnyVideoClient",
) -> Path:
    """使用 videofetch 下载视频。

    Args:
        url: 视频URL
        output_path: 输出路径
        parser: 解析器名称

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 下载失败
    """
    if output_path is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="video_download_"))
        work_dir = temp_dir
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = output_path.parent

    import json
    config = json.dumps({"work_dir": str(work_dir)})

    cmd = [
        "videodl",
        "-i", url,
        "-g",
        "-a", parser,
        "-c", config,
    ]

    print(f"下载视频 (videofetch/{parser}): {url}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        # videofetch 实际会把文件下载到 ./videodl_outputs/{parser}/ 目录
        # 忽略 work_dir 配置,需要从默认目录查找
        default_output = Path("videodl_outputs") / parser

        # 先检查 work_dir
        downloaded_files = list(work_dir.glob("*.mp4"))
        if not downloaded_files:
            downloaded_files = list(work_dir.glob("*.m4v"))
            downloaded_files.extend(list(work_dir.glob("*.mov")))

        # 再检查默认输出目录
        if not downloaded_files and default_output.exists():
            downloaded_files = list(default_output.glob("*.mp4"))
            if not downloaded_files:
                downloaded_files = list(default_output.glob("*.m4v"))
                downloaded_files.extend(list(default_output.glob("*.mov")))

        if downloaded_files:
            # 找到最新下载的文件
            actual_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)

            if output_path:
                # 移动到目标位置
                if actual_file != output_path:
                    import shutil
                    shutil.move(str(actual_file), str(output_path))
                    final_path = output_path
                else:
                    final_path = actual_file
            else:
                final_path = actual_file

            print(f"下载完成: {final_path}")
            return final_path

        error_msg = f"videofetch 下载失败\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        raise RuntimeError(error_msg)

    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"下载超时(300s): {url}") from e
    except Exception as e:
        raise RuntimeError(f"videofetch 下载出错: {e}") from e


def download_video(
    url: str,
    output_path: Optional[Path] = None,
) -> Path:
    """下载视频到本地。

    支持抖音、小红书、快手、TikTok等平台。
    优先使用 you-get,失败则尝试 videofetch。

    Args:
        url: 视频URL(支持分享链接、直链等)
        output_path: 输出路径,留空则自动生成临时文件

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 下载失败
    """
    errors = []

    # 优先尝试 you-get
    try:
        return download_with_youget(url, output_path)
    except Exception as e:
        errors.append(f"you-get: {e}")
        print(f"you-get 失败: {e}")
        print("尝试 videofetch...")

    # 回退到 videofetch
    parsers = [
        "SnapAnyVideoClient",
        "VideoFKVideoClient",
        "GVVideoClient",
        "AnyFetcherVideoClient",
    ]

    for parser in parsers:
        try:
            return download_with_videofetch(url, output_path, parser)
        except Exception as e:
            errors.append(f"videofetch/{parser}: {e}")
            print(f"解析器 {parser} 失败,尝试下一个...")
            continue

    # 所有方法都失败
    error_summary = "\n".join(errors)
    raise RuntimeError(f"所有下载方法都失败:\n{error_summary}")


def download_with_fallback(
    url: str,
    output_path: Optional[Path] = None,
    parsers: Optional[list[str]] = None,
) -> Path:
    """下载视频,自动尝试多种方法。

    Args:
        url: 视频URL
        output_path: 输出路径
        parsers: (已废弃,保留兼容性)

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 所有方法都失败
    """
    return download_video(url, output_path)
