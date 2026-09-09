"""Paid acceptance check through the same API used by the frontend."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.tests.test_api import account_payload, HEADERS

root = Path(__file__).resolve().parents[1]
output = root / "outputs/live-tests/minimal-live-api"
output.mkdir(parents=True, exist_ok=True)
report = {}


def save():
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))


def wait(client, response):
    response.raise_for_status()
    identifier = response.json()["id"]
    previous = None
    deadline = time.monotonic() + 1500
    while time.monotonic() < deadline:
        job = client.get("/api/jobs/" + identifier).json()
        if job["stage"] != previous:
            print(job["kind"], job["stage"], flush=True)
            previous = job["stage"]
        if job["status"] == "completed":
            return job["result"]
        if job["status"] == "failed":
            raise RuntimeError(job["error"])
        time.sleep(3)
    raise TimeoutError(identifier)


try:
    with TestClient(create_app(output / "runtime"), headers=HEADERS) as client:
        client.put("/api/account", json=account_payload()).raise_for_status()
        source = Path(sys.argv[1])
        with source.open("rb") as stream:
            response = client.post("/api/uploads", files={"file": ("reference.mp4", stream, "video/mp4")})
        response.raise_for_status()
        upload = response.json()
        analysis = wait(client, client.post("/api/analyses", json={
            "mode": "live", "title": "真实视频内测", "uploadId": upload["id"]}))
        report["analysis"] = analysis
        save()
        characters = [
            {"id": "account-2", "source": "library", "emoji": "", "name": "铁柱", "desc": "憨厚乐观的柴犬，男声", "accent": "#fde8c8", "img": "/avatars/tiezhu.png"},
            {"id": "account-1", "source": "library", "emoji": "", "name": "甜甜", "desc": "冷静毒舌的三花猫，女声", "accent": "#eef2ff", "img": "/avatars/tiantian.png"}]
        draft = wait(client, client.post("/api/drafts", json={"mode": "live",
            "topic": "萌宠吐槽人类一边健身一边喝奶茶，原创反转短剧", "analysisId": analysis["id"], "characters": characters}))
        report["draft"] = draft
        save()
        draft = wait(client, client.post("/api/drafts/" + draft["id"] + "/video"))
        report["draft"] = draft
        response = client.get(draft["video"]["url"])
        response.raise_for_status()
        (output / "video.mp4").write_bytes(response.content)
        response = client.post("/api/drafts/" + draft["id"] + "/export")
        response.raise_for_status()
        export = response.json()
        package = client.get(export["url"])
        package.raise_for_status()
        (output / "package.zip").write_bytes(package.content)
        report["export"] = export
        report["status"] = "generated"
        save()
    with TestClient(create_app(output / "runtime"), headers=HEADERS) as client:
        restored = client.get("/api/drafts/" + draft["id"])
        restored.raise_for_status()
        assert restored.json()["video"]["taskId"] == draft["video"]["taskId"]
        assert client.get(draft["video"]["url"]).status_code == 200
    report["status"] = "passed"
    report["restart_restore"] = True
    save()
    print("PASSED", str(output), flush=True)
except Exception as exc:
    report["status"] = "failed"
    report["error"] = str(exc)
    save()
    raise
