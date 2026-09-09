"""视频下载器:支持抖音、小红书等平台的无水印视频下载。

优先使用纯 Python requests 下载(无需外部工具),
失败则回退到 you-get 或 videofetch。
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import requests

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
PC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _resolve_short_url(url: str) -> str:
    """解析短链接,获取最终跳转URL。"""
    r = requests.get(url, allow_redirects=True, timeout=15, headers={"User-Agent": MOBILE_UA})
    return r.url


def _extract_xhs_video_url(html: str, page_url: str) -> str:
    """从小红书页面HTML中提取视频直链。"""
    state_match = re.search(r'__INITIAL_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
    if not state_match:
        raise RuntimeError("未找到 __INITIAL_STATE__ 数据")

    raw = state_match.group(1)
    raw_fixed = re.sub(r':\s*undefined\s*,', ': null,', raw)
    raw_fixed = re.sub(r':\s*undefined\s*}', ': null}', raw_fixed)
    raw_fixed = re.sub(r':\s*undefined\s*\n', ': null\n', raw_fixed)

    try:
        data = json.loads(raw_fixed)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析 __INITIAL_STATE__ JSON 失败: {e}") from e

    note_data = data.get("noteData", {})
    inner_data = note_data.get("data", {})
    note_detail = inner_data.get("noteData", {})

    if not note_detail:
        note_detail_map = inner_data.get("noteDetailMap", {})
        first_key = next(iter(note_detail_map), None)
        if first_key and isinstance(note_detail_map[first_key], dict):
            note_detail = note_detail_map[first_key].get("note", note_detail_map[first_key])

    video_info = note_detail.get("video", {})
    if not video_info:
        raise RuntimeError("页面中未找到视频数据(可能是图文笔记)")

    media = video_info.get("media", {})
    stream = media.get("stream", {})

    preferred_codecs = ["h264", "h265", "av1", "h266"]
    for codec in preferred_codecs:
        codec_streams = stream.get(codec, [])
        if isinstance(codec_streams, list) and codec_streams:
            best = max(codec_streams, key=lambda s: s.get("videoBitrate", 0) if isinstance(s, dict) else 0)
            master_url = best.get("masterUrl", "")
            if master_url:
                if master_url.startswith("http://"):
                    master_url = "https://" + master_url[7:]
                return master_url

    raise RuntimeError("未找到可用的视频流地址")


def _extract_douyin_video_url(html: str, page_url: str) -> str:
    """从抖音页面HTML中提取视频直链。"""
    render_data_match = re.search(r'<script\s+id="RENDER_DATA"\s+type="text/javascript">(.+?)</script>', html)
    if not render_data_match:
        state_match = re.search(r'_SSR_HYDRATED_DATA\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if not state_match:
            raise RuntimeError("未找到抖音页面数据")
        raw = state_match.group(1)
        raw_fixed = re.sub(r':\s*undefined\s*,', ': null,', raw)
        raw_fixed = re.sub(r':\s*undefined\s*}', ': null}', raw_fixed)
        try:
            data = json.loads(raw_fixed)
        except json.JSONDecodeError:
            raise RuntimeError("解析抖音 SSR 数据失败")
    else:
        from urllib.parse import unquote
        raw = unquote(render_data_match.group(1))
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError("解析抖音 RENDER_DATA 失败")

    video_url = None
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                detail = value.get("awemeDetail", value.get("aweme_detail", {}))
                if isinstance(detail, dict):
                    vid = detail.get("video", {})
                    play_addr = vid.get("playAddr", vid.get("play_addr", {}))
                    if isinstance(play_addr, dict):
                        url_list = play_addr.get("urlList", play_addr.get("url_list", []))
                        if url_list:
                            video_url = url_list[0]
                            break

    if not video_url:
        all_urls = re.findall(r'(https?://[^\s"]+\.mp4[^\s"]*)', html)
        if all_urls:
            video_url = all_urls[0]

    if not video_url:
        raise RuntimeError("未找到抖音视频地址")

    if video_url.startswith("http://"):
        video_url = "https://" + video_url[7:]

    return video_url


def download_with_requests(
    url: str,
    output_path: Optional[Path] = None,
) -> Path:
    """使用纯 Python requests 下载视频(无需外部CLI工具)。

    支持小红书(xhslink.com)、抖音(v.douyin.com)等平台短链接,
    自动解析跳转并提取无水印视频直链。

    Args:
        url: 视频URL(支持分享链接、短链接、直链)
        output_path: 输出路径,留空则自动生成临时文件

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 下载失败
    """
    if output_path is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="video_download_"))
        final_path = temp_dir / "video.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_path = output_path

    resolved_url = url
    is_short_link = any(domain in url for domain in ["xhslink.com", "v.douyin.com", "www.iesdouyin.com"])

    if is_short_link:
        print(f"解析短链接: {url}")
        resolved_url = _resolve_short_url(url)
        print(f"跳转到: {resolved_url}")

    video_direct_url = None
    referer = ""

    if "xiaohongshu.com" in resolved_url or "xhslink.com" in resolved_url:
        print(f"下载视频 (小红书直解): {resolved_url}")
        referer = "https://www.xiaohongshu.com/"
        r = requests.get(resolved_url, headers={"User-Agent": MOBILE_UA}, timeout=15)
        r.raise_for_status()
        video_direct_url = _extract_xhs_video_url(r.text, resolved_url)

    elif "douyin.com" in resolved_url or "iesdouyin.com" in resolved_url:
        print(f"下载视频 (抖音直解): {resolved_url}")
        referer = "https://www.douyin.com/"
        r = requests.get(resolved_url, headers={"User-Agent": PC_UA}, timeout=15)
        r.raise_for_status()
        video_direct_url = _extract_douyin_video_url(r.text, resolved_url)

    if video_direct_url:
        print(f"视频直链: {video_direct_url[:120]}...")
        headers = {"User-Agent": MOBILE_UA, "Referer": referer}
        r = requests.get(video_direct_url, headers=headers, stream=True, timeout=120)
        r.raise_for_status()

        total_size = int(r.headers.get("Content-Length", 0))
        size_mb = total_size / 1024 / 1024 if total_size else 0
        print(f"开始下载 ({size_mb:.1f} MB)...")

        with final_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"下载完成: {final_path}")
        return final_path

    if resolved_url.endswith(".mp4") or ".mp4?" in resolved_url:
        print(f"直接下载视频: {resolved_url[:120]}...")
        r = requests.get(resolved_url, headers={"User-Agent": MOBILE_UA}, stream=True, timeout=120)
        r.raise_for_status()

        with final_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"下载完成: {final_path}")
        return final_path

    raise RuntimeError("无法从该URL提取视频直链")


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
        temp_dir = Path(tempfile.mkdtemp(prefix="video_download_"))
        work_dir = temp_dir
        output_filename = None
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = output_path.parent
        output_filename = output_path.stem

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

        downloaded_files = list(work_dir.glob("*.mp4"))
        if not downloaded_files:
            downloaded_files = list(work_dir.glob("*.m4v"))
            downloaded_files.extend(list(work_dir.glob("*.mov")))
            downloaded_files.extend(list(work_dir.glob("*.flv")))

        if downloaded_files:
            actual_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)

            if output_path and actual_file != output_path:
                if actual_file.suffix != ".mp4":
                    final_path = output_path.with_suffix(actual_file.suffix)
                else:
                    final_path = output_path
                actual_file.rename(final_path)
            else:
                final_path = actual_file

            print(f"下载完成: {final_path}")
            return final_path

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

        default_output = Path("videodl_outputs") / parser

        downloaded_files = list(work_dir.glob("*.mp4"))
        if not downloaded_files:
            downloaded_files = list(work_dir.glob("*.m4v"))
            downloaded_files.extend(list(work_dir.glob("*.mov")))

        if not downloaded_files and default_output.exists():
            downloaded_files = list(default_output.glob("*.mp4"))
            if not downloaded_files:
                downloaded_files = list(default_output.glob("*.m4v"))
                downloaded_files.extend(list(default_output.glob("*.mov")))

        if downloaded_files:
            actual_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)

            if output_path:
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
    优先使用纯 Python requests 直解(无需外部工具),
    失败则回退到 you-get,再失败则尝试 videofetch。

    Args:
        url: 视频URL(支持分享链接、直链等)
        output_path: 输出路径,留空则自动生成临时文件

    Returns:
        下载后的本地视频路径

    Raises:
        RuntimeError: 下载失败
    """
    errors = []

    try:
        return download_with_requests(url, output_path)
    except Exception as e:
        errors.append(f"requests直解: {e}")
        print(f"requests直解失败: {e}")
        print("尝试 you-get...")

    try:
        return download_with_youget(url, output_path)
    except Exception as e:
        errors.append(f"you-get: {e}")
        print(f"you-get 失败: {e}")
        print("尝试 videofetch...")

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
