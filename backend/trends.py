from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .pipeline import config
from .store import timestamp


class TrendService:
    """Serves the curated, source-verified trend catalog."""

    def __init__(self, catalog_path: Path):
        self._demo = json.loads(catalog_path.read_text("utf-8"))
        self._lock = threading.Lock()
        self._cached: dict[str, Any] | None = None
        self._cached_at = 0.0

    def platform_status(self) -> list[dict[str, Any]]:
        douyin_ready = bool(config.DOUYIN_ACCESS_TOKEN or (config.DOUYIN_CLIENT_KEY and config.DOUYIN_CLIENT_SECRET))
        return [
            {"key": "douyin", "name": "抖音", "mode": "official" if douyin_ready else "demo", "configured": douyin_ready,
             "capabilities": ["热门视频榜", "授权账号数据", "视频发布"]},
            {"key": "kuaishou", "name": "快手", "mode": "demo", "configured": False,
             "capabilities": ["授权账号作品数据", "视频发布"]},
            {"key": "xhs", "name": "小红书", "mode": "demo", "configured": False,
             "capabilities": ["小程序经营能力"]},
            {"key": "bili", "name": "B站", "mode": "demo", "configured": False,
             "capabilities": ["授权账号稿件数据", "稿件发布"]},
            {"key": "shipinhao", "name": "视频号", "mode": "demo", "configured": False,
             "capabilities": ["待平台开放能力"]},
        ]

    def catalog(self, range_key: str = "24h") -> dict[str, Any]:
        if range_key not in {"24h", "7d", "30d"}:
            raise ValueError("时间范围仅支持 24h、7d 或 30d")
        with self._lock:
            if self._cached and time.monotonic() - self._cached_at < 600:
                result = copy.deepcopy(self._cached)
                result["range"] = range_key
                return result
            result = copy.deepcopy(self._demo)
            result.update({"range": range_key, "providers": self.platform_status(), "fetchedAt": timestamp()})
            self._cached = copy.deepcopy(result)
            self._cached_at = time.monotonic()
            return result

    def _douyin_token(self) -> str:
        if config.DOUYIN_ACCESS_TOKEN:
            return config.DOUYIN_ACCESS_TOKEN
        response = requests.post(
            "https://open.douyin.com/oauth/client_token/",
            data={"client_key": config.DOUYIN_CLIENT_KEY, "client_secret": config.DOUYIN_CLIENT_SECRET,
                  "grant_type": "client_credential"},
            timeout=config.PLATFORM_HTTP_TIMEOUT,
        )
        payload = self._json(response)
        token = (payload.get("data") or {}).get("access_token") or payload.get("access_token")
        if response.status_code != 200 or not token:
            raise RuntimeError("抖音应用令牌获取失败，请检查应用资质和凭据")
        return token

    def _douyin_hot_videos(self) -> list[dict[str, Any]]:
        response = requests.get(
            config.DOUYIN_HOT_API_URL,
            headers={"access-token": self._douyin_token(), "Content-Type": "application/json"},
            timeout=config.PLATFORM_HTTP_TIMEOUT,
        )
        payload = self._json(response)
        if response.status_code != 200:
            raise RuntimeError("抖音热门视频接口请求失败")
        data = payload.get("data") or payload
        raw_items = data.get("list") or data.get("videos") or data.get("items") or []
        videos = []
        for index, item in enumerate(raw_items[:12]):
            video_id = str(item.get("video_id") or item.get("item_id") or item.get("id") or f"douyin-{index}")
            stats = item.get("statistics") or item.get("stats") or {}
            videos.append({
                "id": "douyin-" + video_id,
                "platform": "douyin",
                "title": item.get("video_title") or item.get("title") or "抖音热门视频",
                "author": item.get("author_name") or item.get("nickname") or "抖音创作者",
                "url": item.get("video_play_url") or item.get("share_url") or f"https://www.douyin.com/video/{video_id}",
                "poster": item.get("cover") or item.get("cover_url") or "",
                "likes": self._compact(item.get("digg_count") or stats.get("digg_count") or stats.get("like_count")),
                "plays": self._compact(item.get("play_count") or stats.get("play_count") or item.get("hot_value")),
                "angle": "来自抖音官方热门视频榜，建议进入爆款拆解后提炼原创结构",
                "publishedAt": str(item.get("create_time") or "今日"),
                "category": "抖音热门",
                "metricsMode": "official",
            })
        return videos

    @staticmethod
    def _compact(value: Any) -> str:
        try:
            number = int(value or 0)
        except (TypeError, ValueError):
            return "--"
        if number >= 10000:
            return f"{number / 10000:.1f}万"
        return f"{number:,}"

    @staticmethod
    def _json(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {}
        except ValueError as error:
            raise RuntimeError("平台接口未返回有效 JSON") from error

    @staticmethod
    def _safe_provider_error(error: Exception) -> str:
        message = str(error).replace(config.DOUYIN_ACCESS_TOKEN, "[redacted]") if config.DOUYIN_ACCESS_TOKEN else str(error)
        return message[:240]
