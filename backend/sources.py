from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse
import requests
from yt_dlp import YoutubeDL
from imageio_ffmpeg import get_ffmpeg_exe
from .pipeline.video_downloader import _extract_douyin_video_url, _extract_xhs_video_url

PAGE_HOSTS = (
    "douyin.com", "iesdouyin.com", "xiaohongshu.com", "xhslink.com",
    "bilibili.com", "b23.tv", "kuaishou.com", "v.kuaishou.com",
    "weixin.qq.com", "channels.weixin.qq.com",
)
MEDIA_HOSTS = PAGE_HOSTS + (
    "douyinvod.com", "byteoversea.com", "xhscdn.com", "bilivideo.com",
    "ks-cdn.com", "kwaicdn.com", "aliyuncs.com",
)


def safe_url(url: str, hosts=None):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("只支持不含账号凭据的 HTTPS 公网地址")
    if hosts and not any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in hosts):
        raise ValueError("该平台暂不支持直接解析，请上传有使用权限的视频，或粘贴字幕进行文字拆解")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("不允许访问本地或私有网络地址")
    return url


def resolve_video(url: str) -> str:
    if urlparse(url).path.lower().endswith((".mp4", ".mov")):
        return safe_url(url, MEDIA_HOSTS)
    current = safe_url(url, PAGE_HOSTS)
    with requests.Session() as session:
        session.trust_env = False
        for _ in range(5):
            safe_url(current, PAGE_HOSTS)
            with session.get(current, allow_redirects=False, stream=True, timeout=(10, 20),
                             headers={"User-Agent": "Mozilla/5.0 CreatorOS/0.2"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    current = urljoin(current, response.headers.get("Location", ""))
                    continue
                if response.status_code in (401, 403, 429):
                    raise ValueError("平台要求登录、授权或限制访问，请上传原视频；不会绕过平台限制")
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > 2 * 1024 * 1024:
                        raise ValueError("平台页面过大，请改为上传视频")
                html = content.decode("utf-8", errors="replace")
                host = urlparse(current).hostname or ""
                try:
                    direct = (_extract_xhs_video_url(html, current) if "xiaohongshu" in host or "xhslink" in host
                              else _extract_douyin_video_url(html, current))
                except RuntimeError as error:
                    raise ValueError("未能从公开页面读取视频，请上传原视频或粘贴字幕") from error
                return safe_url(direct, MEDIA_HOSTS)
    raise ValueError("平台链接跳转过多，请上传视频")


def download_public_video(url: str, output_dir, max_bytes: int = 64 * 1024 * 1024):
    """Download one supported public video without playlists or authentication bypass."""
    from pathlib import Path

    safe_url(url, PAGE_HOSTS + MEDIA_HOSTS)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "source.%(ext)s")
    options = {
        "outtmpl": template,
        "format": "bv*[height<=720]+ba/b[height<=720]/best",
        "merge_output_format": "mp4",
        "ffmpeg_location": get_ffmpeg_exe(),
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        "noplaylist": True,
        "max_filesize": max_bytes,
        "socket_timeout": 20,
        "retries": 1,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
            expected = Path(downloader.prepare_filename(info))
    except Exception as error:
        raise ValueError("未能读取该平台视频，请上传有使用权限的原视频") from error
    candidates = [expected] + sorted(output_dir.glob("source.*"))
    target = next((path for path in candidates if path.is_file()), None)
    if target is None or target.stat().st_size < 1024:
        raise ValueError("平台没有返回可分析的视频文件")
    if target.stat().st_size > max_bytes:
        target.unlink(missing_ok=True)
        raise ValueError("链接视频超过 64 MB，请上传压缩后的版本")
    return target
