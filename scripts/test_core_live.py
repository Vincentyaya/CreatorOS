"""Opt-in production-core test using non-sensitive prompts and configured providers."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    os.environ["CREATOROS_ENV_FILE"] = str(args.env_file)
    os.environ.setdefault("VIDEO_RENDER_STRATEGY", "compose")
    output = ROOT / "outputs" / "live-tests" / (time.strftime("%Y%m%d-%H%M%S") + "-core")
    output.mkdir(parents=True)

    from fastapi.testclient import TestClient
    from backend.app import create_app

    app = create_app(output / "api-data")
    headers = {"X-CreatorOS-Client": "local-preview"}
    report = {"output": str(output), "stages": []}

    def record(stage, **details):
        report["stages"].append({"stage": stage, **details})
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report["stages"][-1], ensure_ascii=False), flush=True)

    def expect(response):
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
        return response.json()

    def wait_job(client, job, timeout=420):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            current = expect(client.get("/api/jobs/" + job["id"]))
            if current["stage"] != last:
                last = current["stage"]
                print(json.dumps({"progress": last}, ensure_ascii=False), flush=True)
            if current["status"] == "completed":
                return current["result"]
            if current["status"] == "failed":
                raise RuntimeError(current["error"])
            time.sleep(1)
        raise TimeoutError("job timed out")

    account = {
        "profile": {"name": "人类观察日记", "niche": "萌宠 + 职场脱口秀", "audience": "年轻职场人",
                    "valueProposition": "用萌宠视角观察人类生活", "contentPreferences": "双角色对话，结尾反转",
                    "formats": ["短视频"], "tone": "轻松幽默", "duration": 15, "platforms": ["抖音"]},
        "chars": [{"id": 1, "emoji": "", "name": "甜甜", "meta": "三花猫", "persona": "人间清醒",
                   "quirk": "冷静反转", "accent": "#eef2ff", "avatar": "/avatars/tiantian.png"}],
        "interaction": "甜甜负责反转，新角色负责捧哏", "forbidden": ["不人身攻击", "不复制参考台词"],
    }

    with TestClient(app, headers=headers) as client:
        expect(client.put("/api/account", json=account))
        avatar = wait_job(client, expect(client.post("/api/avatars", json={
            "name": "新铁柱", "prompt": "原创柴犬脱口秀主持人，憨厚热情，表情丰富，精致三维动画风格",
        })))
        record("avatar", status="ok", provider=avatar.get("provider"), model=avatar.get("model"), bytes=avatar["size"])

        analysis = wait_job(client, expect(client.post("/api/analyses", json={
            "mode": "live", "title": "职场反差结构测试",
            "transcript": "开场先共情打工人的疲惫，第二句用萌宠视角反问，第三句夸张升级，最后用一句冷幽默完成反转。",
        })))
        record("analysis", status="ok", evidence=analysis["evidence"], shots=len(analysis["reverse"]["shots"]))

        draft = wait_job(client, expect(client.post("/api/drafts", json={
            "mode": "live", "topic": "为什么人类下班后还要开会", "analysisId": analysis["id"],
            "characters": [
                {"id": "account-1", "source": "library", "name": "甜甜", "desc": "人间清醒",
                 "emoji": "", "accent": "#eef2ff", "img": "/avatars/tiantian.png"},
                {"id": avatar["id"], "source": "generated", "name": "新铁柱", "desc": "憨厚热情",
                 "emoji": "", "accent": "#fde8c8", "img": avatar["url"]},
            ],
        })))
        record("script", status="ok", title=draft["script"]["title"], scenes=len(draft["script"]["scenes"]))

        rendered = wait_job(client, expect(client.post(f"/api/drafts/{draft['id']}/video")))
        video_response = client.get(rendered["video"]["url"])
        video_path = output / "generated-video.mp4"
        video_path.write_bytes(video_response.content)
        record("video", status="ok", provider=rendered["video"].get("provider"), bytes=len(video_response.content))

        exported = expect(client.post(f"/api/drafts/{draft['id']}/export"))
        package = client.get(exported["url"])
        (output / "creatoros-publish.zip").write_bytes(package.content)
        record("export", status="ok", bytes=len(package.content), containsVideo=exported["containsVideo"])

    print(json.dumps({"report": str(output / "report.json"), "video": str(video_path)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
