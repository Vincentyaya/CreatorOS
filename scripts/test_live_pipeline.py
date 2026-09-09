"""Opt-in live provider test; artifacts and database are isolated from the workspace."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--generate-video", action="store_true")
    args = parser.parse_args()
    os.environ["CREATOROS_ENV_FILE"] = str(args.env_file)
    output = ROOT / "outputs" / "live-tests" / time.strftime("%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    os.environ["CREATOROS_DATA_DIR"] = str(output / "api-data")

    from fastapi.testclient import TestClient
    from imageio_ffmpeg import read_frames
    from backend.app import app
    from backend.jobs import safe_error
    from backend.pipeline import volc_base
    from backend.pipeline.xiaoyunque_client import create_client

    results = []
    report = {"video": str(args.video), "output": str(output), "stages": results, "published": False}

    def persist():
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(stage, status, **details):
        result = {"stage": stage, "status": status, **details}
        results.append(result)
        persist()
        print(json.dumps(result, ensure_ascii=False), flush=True)

    frames = read_frames(str(args.video))
    try:
        metadata = next(frames)
        report["videoMetadata"] = {key: value for key, value in metadata.items() if key != "ffmpeg_version"}
    finally:
        frames.close()
    persist()

    chars = [
        {"id": 1, "emoji": "", "name": "甜甜", "meta": "三花猫", "persona": "人间清醒，善于冷幽默", "quirk": "人类真是想太多", "accent": "#e0e7ff", "avatar": "/avatars/tiantian.png"},
        {"id": 2, "emoji": "", "name": "铁柱", "meta": "柴犬", "persona": "憨厚热情，容易相信人类", "quirk": "我觉得这事儿能行", "accent": "#fde8c8", "avatar": "/avatars/tiezhu.png"},
    ]
    account = {
        "profile": {"name": "人类观察日记 · 接口测试", "niche": "萌宠 + 生活脱口秀",
                    "audience": "喜欢萌宠和生活吐槽的年轻人", "valueProposition": "用萌宠的视角发现人类生活中的小矛盾",
                    "contentPreferences": "猫狗双角色对话，轻松吐槽，原创梗，不复制参考视频台词",
                    "formats": ["短视频"], "tone": "轻松幽默", "duration": 15, "platforms": ["抖音"]},
        "chars": chars, "interaction": "铁柱负责捧哏，甜甜负责反转", "forbidden": ["不人身攻击", "不贩卖身材焦虑"],
    }
    headers = {"X-CreatorOS-Client": "local-preview"}

    def expect(response):
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.json().get('detail', 'request failed')}")
        return response.json()

    with TestClient(app, headers=headers) as client:
        def wait_job(job, timeout=360):
            deadline = time.monotonic() + timeout
            previous = ""
            while time.monotonic() < deadline:
                current = expect(client.get("/api/jobs/" + job["id"]))
                if current["stage"] != previous:
                    previous = current["stage"]
                    print(json.dumps({"job": job["id"], "progress": previous}, ensure_ascii=False), flush=True)
                if current["status"] == "completed":
                    return current["result"]
                if current["status"] == "failed":
                    raise RuntimeError(current["error"])
                time.sleep(2)
            raise TimeoutError("Live test job timed out")

        stage = "upload"
        draft = None
        try:
            expect(client.put("/api/account", json=account))
            with args.video.open("rb") as file:
                uploaded = expect(client.post("/api/uploads", files={"file": (args.video.name, file, "video/mp4")}))
            served = client.get(uploaded["url"])
            assert served.status_code == 200
            assert hashlib.sha256(served.content).digest() == hashlib.sha256(args.video.read_bytes()).digest()
            record(stage, "ok", uploadId=uploaded["id"], size=uploaded["size"])

            stage = "video_analysis"
            start = time.monotonic()
            analysis = wait_job(expect(client.post("/api/analyses", json={
                "mode": "live", "title": args.video.stem, "uploadId": uploaded["id"], "transcript": "",
            })))
            (output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
            assert analysis["evidence"] in {"video", "keyframes"} and analysis["reverse"]["shots"]
            record(stage, "ok", seconds=round(time.monotonic() - start, 2),
                   shots=len(analysis["reverse"]["shots"]), summary=analysis["reverse"]["summary"])

            stage = "script_generation"
            draft = wait_job(expect(client.post("/api/drafts", json={
                "mode": "live", "topic": "健身后的奶茶奖励，用猫狗对话写一个不同于参考片的原创反转",
                "analysisId": analysis["id"],
                "characters": [{"id": "account-" + str(c["id"]), "source": "library", "name": c["name"],
                                "desc": c["persona"], "emoji": c["emoji"], "accent": c["accent"], "img": c["avatar"]} for c in chars],
            })))
            (output / "draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
            record(stage, "ok", title=draft["script"]["title"], scenes=len(draft["script"]["scenes"]))

            stage = "edit_and_export"
            script = draft["script"]
            script["caption"] += "\n\n（测试草稿，未发布）"
            draft = expect(client.patch("/api/drafts/" + draft["id"], json={"revision": draft["revision"], "script": script}))
            export = expect(client.post("/api/drafts/" + draft["id"] + "/export"))
            package = client.get(export["url"])
            assert package.status_code == 200
            with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
                assert archive.read("caption.txt").decode("utf-8") == script["caption"]
            (output / "publish-copy.zip").write_bytes(package.content)
            record(stage, "ok", containsVideo=export["containsVideo"])
        except Exception as error:
            record(stage, "failed", errorType=type(error).__name__, error=safe_error(error))

        # A query for a deliberately nonexistent task checks reachability without creating a video.
        stage = "video_service_probe"
        try:
            service = create_client()
            response = volc_base.call(service._service, "CVSync2AsyncGetResult",
                                      {"req_key": "pippit_iv2v_v20_cvtob_with_vinput", "task_id": "creatoros-connectivity-probe"},
                                      "小云雀")
            response_text = safe_error(json.dumps(response, ensure_ascii=False))
            denied = any(term in response_text.lower() for term in ("accessdenied", "access denied", "unauthorized", "invalidaccesskey", "signaturedoesnotmatch"))
            report["videoProbe"] = response
            record(stage, "denied" if denied else "responded", response=response_text,
                   note="不存在的测试任务查询，不等于已成功生成视频")
            if args.generate_video and draft and not denied:
                stage = "video_generation"
                rendered = wait_job(expect(client.post("/api/drafts/" + draft["id"] + "/video")), timeout=1500)
                video = client.get(rendered["video"]["url"])
                assert video.status_code == 200 and len(video.content) > 1024
                (output / "generated-video.mp4").write_bytes(video.content)
                record(stage, "ok", bytes=len(video.content))
        except Exception as error:
            record(stage, "failed", errorType=type(error).__name__, error=safe_error(error))
    persist()
    print(json.dumps({"report": str(output / "report.json"), "stages": results}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
