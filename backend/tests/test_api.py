from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


HEADERS = {"X-CreatorOS-Client": "local-preview"}


def account_payload():
    return {
        "profile": {
            "avatar": "/avatars/tiantian.png",
            "name": "人类观察日记",
            "niche": "萌宠 + 职场脱口秀",
            "audience": "年轻职场人",
            "valueProposition": "用萌宠视角观察人类生活",
            "contentPreferences": "双角色对话，结尾反转",
            "formats": ["短视频"],
            "tone": "轻松幽默",
            "duration": 30,
            "platforms": ["抖音", "B站"],
        },
        "chars": [
            {"id": 1, "emoji": "", "name": "甜甜", "meta": "三花猫", "persona": "人间清醒",
             "quirk": "别套近乎", "accent": "#eef2ff", "avatar": "/avatars/tiantian.png"},
            {"id": 2, "emoji": "", "name": "铁柱", "meta": "柴犬", "persona": "盲目乐观",
             "quirk": "我觉得能行", "accent": "#fde8c8", "avatar": "/avatars/tiezhu.png"},
        ],
        "interaction": "甜甜负责反转，铁柱负责捧哏",
        "forbidden": ["不人身攻击"],
    }


def wait_job(client: TestClient, identifier: str, timeout: float = 30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{identifier}").json()
        if job["status"] == "completed":
            return job["result"]
        if job["status"] == "failed":
            raise AssertionError(job["error"])
        time.sleep(0.1)
    raise AssertionError("job timed out")


def test_product_demo_flow(tmp_path: Path):
    app = create_app(tmp_path)
    with TestClient(app, headers=HEADERS) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["capabilities"]["video"] is True

        saved = client.put("/api/account", json=account_payload())
        assert saved.status_code == 200
        assert client.get("/api/account").json()["account"]["profile"]["avatar"] == "/avatars/tiantian.png"

        catalog = client.get("/api/catalog?range=7d")
        assert catalog.status_code == 200
        references = catalog.json()["videos"]
        assert len(references) == 6
        assert {video["platform"] for video in references} == {"xhs", "bili"}
        assert len(catalog.json()["picks"]) == 3
        assert len(client.get("/api/platforms").json()) == 5
        for reference in references:
            assert reference["localReference"] is True
            expected_host = "xhslink.cn" if reference["platform"] == "xhs" else "b23.tv"
            assert reference["url"].startswith(f"https://{expected_host}/")
            cover = client.get(reference["poster"])
            assert cover.status_code == 200 and cover.headers["content-type"] == "image/jpeg"
            video = client.get(f"/api/trends/{reference['id']}/video")
            assert video.status_code == 200 and video.headers["content-type"] == "video/mp4"
            assert len(video.content) > 1024

        topic = client.post("/api/topics", json={
            "id": "topic-test", "topic": "复盘推荐选题", "angle": "用猫狗对话讲职场反差",
            "referenceId": "review-test", "status": "待研究", "source": "review",
        })
        assert topic.status_code == 201
        assert client.get("/api/topics").json()[0]["id"] == "topic-test"
        assert client.patch("/api/topics/topic-test", json={"status": "已生成"}).json()["status"] == "已生成"

        analysis_job = client.post("/api/analyses", json={
            "mode": "demo", "title": "参考内容", "transcript": "一段用于演示的观察笔记",
        })
        assert analysis_job.status_code == 202
        analysis = wait_job(client, analysis_job.json()["id"])
        assert analysis["evidence"] == "demo"

        draft_job = client.post("/api/drafts", json={
            "mode": "demo", "topic": "打工人和狗谁更累", "analysisId": analysis["id"],
            "characters": [
                {"id": "account-1", "source": "library", "emoji": "", "name": "甜甜", "desc": "人间清醒", "accent": "#eef2ff", "img": "/avatars/tiantian.png"},
                {"id": "account-2", "source": "library", "emoji": "", "name": "铁柱", "desc": "盲目乐观", "accent": "#fde8c8", "img": "/avatars/tiezhu.png"},
            ],
        })
        draft = wait_job(client, draft_job.json()["id"])
        assert len(draft["script"]["scenes"]) == 4

        video_job = client.post(f"/api/drafts/{draft['id']}/video")
        assert video_job.status_code == 202
        rendered = wait_job(client, video_job.json()["id"], timeout=60)
        video = client.get(rendered["video"]["url"])
        assert video.status_code == 200 and len(video.content) > 1024
        assert rendered["video"]["provider"] == "creatoros-compose"
        assert rendered["video"]["audio"] == "system-tts"
        assert b"mp4a" in video.content

        queued = client.post(f"/api/drafts/{draft['id']}/queue", json={"platforms": ["抖音", "B站"]})
        assert queued.status_code == 201
        assert queued.json()["status"] == "awaiting_authorization"

        exported = client.post(f"/api/drafts/{draft['id']}/export")
        package = client.get(exported.json()["url"])
        assert package.status_code == 200 and package.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
            assert {"video.mp4", "script.json", "video-prompts.json", "reverse-analysis.json"} <= set(archive.namelist())

        assert client.delete("/api/topics/topic-test").json() == {"ok": True}
        assert client.get("/api/topics").json() == []


def test_modifications_require_workspace_header(tmp_path: Path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/topics", json={"topic": "测试", "angle": "测试选题"})
        assert response.status_code == 403


def test_avatar_generation_job(tmp_path: Path, monkeypatch):
    from PIL import Image
    from backend import engine
    from backend.pipeline import config

    monkeypatch.setattr(config, "IMAGE_API_KEY", "test-key")

    def fake_avatar(name, prompt, target, update):
        update("生成角色形象")
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (128, 128), (79, 70, 229)).save(target)
        return {"provider": "test", "model": "test-image"}

    monkeypatch.setattr(engine, "generate_avatar", fake_avatar)
    app = create_app(tmp_path)
    with TestClient(app, headers=HEADERS) as client:
        submitted = client.post("/api/avatars", json={"name": "新角色", "prompt": "原创的三花猫脱口秀主持人"})
        assert submitted.status_code == 202
        avatar = wait_job(client, submitted.json()["id"])
        assert avatar["generated"] is True
        image = client.get(avatar["url"])
        assert image.status_code == 200 and image.headers["content-type"] == "image/png"


def test_catalog_analysis_uses_bound_local_video(tmp_path: Path, monkeypatch):
    from backend import engine

    seen = {}

    def fake_analyze(body, account, upload_path, update, catalog_item=None):
        update("读取本地热点视频")
        seen[body.catalogId] = upload_path
        return {
            "id": f"analysis-{body.catalogId}",
            "mode": body.mode,
            "evidence": "video",
            "source": {
                "title": body.title,
                "url": body.url,
                "uploadId": None,
                "referenceId": body.catalogId,
            },
        }

    monkeypatch.setattr(engine, "analyze", fake_analyze)
    app = create_app(tmp_path)
    with TestClient(app, headers=HEADERS) as client:
        assert client.put("/api/account", json=account_payload()).status_code == 200
        references = client.get("/api/catalog").json()["videos"]
        for reference in references:
            submitted = client.post("/api/analyses", json={
                "mode": "live",
                "catalogId": reference["id"],
                "title": reference["title"],
                "url": reference["url"],
            })
            assert submitted.status_code == 202
            result = wait_job(client, submitted.json()["id"])
            assert result["source"]["referenceId"] == reference["id"]

    assert set(seen) == {reference["id"] for reference in references}
    for identifier, path in seen.items():
        assert path.is_file()
        assert path.parent.name == identifier
        assert path.name == "final_video.mp4"
        assert path.stat().st_size > 1024
