from __future__ import annotations

import json
import os
import zipfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import engine
from .analytics import review
from .jobs import Jobs, safe_error
from .models import Account, AnalysisInput, AvatarInput, GenerateInput, DraftUpdate, QueueInput, TopicInput, TopicUpdate
from .pipeline import publisher
from .pipeline.models import Script
from .store import Store, new_id, timestamp
from .trends import TrendService

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 64 * 1024 * 1024
DEMO_MEDIA = ROOT / "demo_media"
TREND_COVERS = ROOT / "trend_covers"


def create_app(data_dir=None):
    store = Store(Path(data_dir or os.getenv("CREATOROS_DATA_DIR", ROOT / "runtime")))
    jobs = Jobs(store)
    trends = TrendService(ROOT / "catalog.json")

    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.pool.shutdown(wait=True)

    app = FastAPI(title="CreatorOS API", version="0.2.0", lifespan=lifespan)
    app.state.store = store
    app.state.jobs = jobs
    hosts = ["127.0.0.1", "localhost", "testserver", "*.onrender.com"]
    hosts.extend(v.strip() for v in os.getenv("CREATOROS_ALLOWED_HOSTS", "").split(",") if v.strip())
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            allowed = {"http://127.0.0.1:5174", "http://localhost:5174", "http://127.0.0.1:8001", "http://localhost:8001"}
            allowed.update({"http://127.0.0.1:8080", "http://localhost:8080"})
            allowed.update(v.strip() for v in os.getenv("CREATOROS_ALLOWED_ORIGINS", "").split(",") if v.strip())
            host = request.headers.get("host", "")
            same_origin = origin in {f"https://{host}", f"http://{host}"}
            if origin and origin not in allowed and not same_origin:
                return JSONResponse({"detail": "仅允许当前本地工作台发起修改"}, status_code=403)
            if request.headers.get("x-creatoros-client") != "local-preview":
                return JSONResponse({"detail": "缺少工作台请求标识"}, status_code=403)
            maximum = MAX_UPLOAD + 1024 * 1024 if request.url.path == "/api/uploads" else 12 * 1024 * 1024
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > maximum:
                    return JSONResponse({"detail": "请求内容过大"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse({"detail": "输入格式不正确，请检查必填项、字段长度与数值范围"}, status_code=422)

    @app.exception_handler(ValueError)
    async def input_error(request, error):
        return JSONResponse({"detail": safe_error(error)}, status_code=400)

    def require_record(kind, identifier):
        record = store.get(kind, identifier)
        if record is None:
            raise HTTPException(404, "记录不存在")
        return record

    def account():
        record = store.get("account", "default")
        if record is None:
            raise HTTPException(409, "请先保存账号定位")
        return record["settings"]

    def require_capability(name):
        if not engine.capabilities()[name]:
            raise HTTPException(503, "该服务尚未配置模型凭据，请在后端环境文件中配置后重试")

    def trend_media(identifier: str, filename: str):
        if not identifier.replace("-", "").isalnum():
            raise HTTPException(404, "热点视频不存在")
        path = DEMO_MEDIA / identifier / filename
        if not path.is_file():
            raise HTTPException(404, "热点视频素材尚未生成")
        return path

    def trend_cover_path(identifier: str):
        if not identifier.replace("-", "").isalnum():
            raise HTTPException(404, "热点封面不存在")
        path = TREND_COVERS / f"{identifier}.jpg"
        if not path.is_file():
            raise HTTPException(404, "热点封面不存在")
        return path

    def draft_busy(identifier):
        return any(j["kind"] == "video" and j.get("draftId") == identifier and j["status"] in ("queued", "running")
                   for j in store.list("job", 1000))

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "CreatorOS Python", "capabilities": engine.capabilities()}

    @app.get("/api/account")
    def get_account():
        record = store.get("account", "default")
        return {"account": record["settings"] if record else None}

    @app.put("/api/account")
    def save_account(body: Account):
        value = body.model_dump(exclude_none=True)
        store.put("account", {"id": "default", "settings": value})
        return {"account": value}

    @app.get("/api/catalog")
    def catalog(range: str = "24h"):
        return trends.catalog(range)

    @app.get("/api/platforms")
    def platforms():
        return trends.platform_status()

    @app.get("/api/topics")
    def topics():
        return store.list("topic", 200)

    @app.post("/api/topics", status_code=201)
    def create_topic(body: TopicInput):
        value = body.model_dump()
        value["id"] = body.id or new_id()
        value["createdAt"] = timestamp()
        value["updatedAt"] = value["createdAt"]
        return store.put("topic", value)

    @app.patch("/api/topics/{identifier}")
    def update_topic(identifier: str, body: TopicUpdate):
        require_record("topic", identifier)
        return store.patch("topic", identifier, body.model_dump())

    @app.delete("/api/topics/{identifier}")
    def delete_topic(identifier: str):
        if not store.delete("topic", identifier):
            raise HTTPException(404, "选题不存在")
        return {"ok": True}

    @app.get("/api/review")
    def get_review(start: date, end: date, platform: str = "all"):
        return review(start, end, platform)

    @app.post("/api/uploads", status_code=201)
    async def upload(file: UploadFile = File(...)):
        suffixes = {"video/mp4": ".mp4", "video/quicktime": ".mov", "image/png": ".png",
                    "image/jpeg": ".jpg", "image/webp": ".webp"}
        extension = suffixes.get(file.content_type or "")
        if not extension:
            raise HTTPException(415, "只支持 MP4、MOV、PNG、JPG 和 WebP")
        identifier = new_id()
        directory = store.directory / "uploads"
        directory.mkdir(exist_ok=True)
        target = directory / (identifier + extension)
        limit = 5 * 1024 * 1024 if extension in (".png", ".jpg", ".webp") else MAX_UPLOAD
        size = 0
        head = b""
        try:
            with target.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, "图片最大 5 MB，视频最大 64 MB")
                    if not head:
                        head = chunk[:32]
                    output.write(chunk)
            valid = (extension == ".png" and head.startswith(b"\x89PNG\r\n\x1a\n") or
                     extension == ".jpg" and head.startswith(b"\xff\xd8\xff") or
                     extension == ".webp" and head[:4] == b"RIFF" and head[8:12] == b"WEBP" or
                     extension in (".mp4", ".mov") and head[4:8] in (b"ftyp", b"moov", b"wide"))
            if not size or not valid:
                raise HTTPException(415, "文件内容与声明格式不匹配")
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        record = {"id": identifier, "name": Path(file.filename or "upload").name[:200],
                  "extension": extension, "contentType": file.content_type, "size": size,
                  "url": f"/api/uploads/{identifier}", "createdAt": timestamp()}
        store.put("upload", record)
        return record

    @app.get("/api/uploads/{identifier}")
    def upload_file(identifier: str):
        record = require_record("upload", identifier)
        return FileResponse(store.directory / "uploads" / (record["id"] + record["extension"]), media_type=record["contentType"])

    @app.get("/api/analyses")
    def analyses():
        return store.list("analysis")

    @app.post("/api/avatars", status_code=202)
    def generate_avatar(body: AvatarInput):
        require_capability("avatar")
        identifier = new_id()
        target = store.directory / "uploads" / (identifier + ".png")

        def operation(update):
            metadata = engine.generate_avatar(body.name, body.prompt, target, update)
            record = {
                "id": identifier, "name": body.name + ".png", "extension": ".png",
                "contentType": "image/png", "size": target.stat().st_size,
                "url": f"/api/uploads/{identifier}", "createdAt": timestamp(),
                "generated": True, **metadata,
            }
            return store.put("upload", record)

        return jobs.submit("avatar", operation)

    @app.get("/api/analyses/{identifier}")
    def analysis(identifier: str):
        return require_record("analysis", identifier)

    @app.post("/api/analyses", status_code=202)
    def analyze(body: AnalysisInput):
        acct = account()
        if not (body.url.strip() or body.transcript.strip() or body.uploadId or body.catalogId):
            raise HTTPException(400, "请提供视频链接、上传视频或字幕")
        if body.url and not body.catalogId:
            parsed = urlparse(body.url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username:
                raise HTTPException(400, "参考链接必须是 HTTPS 地址")
        if body.mode == "live":
            require_capability("analysis")
        path = None
        catalog_item = None
        if body.catalogId:
            catalog_item = next((item for item in trends.catalog().get("videos", []) if item.get("id") == body.catalogId), None)
            if catalog_item is None:
                raise HTTPException(404, "热点内容不存在")
            path = trend_media(body.catalogId, "final_video.mp4")
        elif body.uploadId:
            uploaded = require_record("upload", body.uploadId)
            if uploaded["extension"] not in (".mp4", ".mov"):
                raise HTTPException(400, "拆解需要上传视频文件")
            path = store.directory / "uploads" / (uploaded["id"] + uploaded["extension"])
        return jobs.submit("analysis", lambda update: store.put("analysis", engine.analyze(body, acct, path, update, catalog_item)))

    @app.get("/api/references/{identifier}/video")
    def reference_video(identifier: str):
        return FileResponse(trend_media(identifier, "final_video.mp4"), media_type="video/mp4")

    @app.get("/api/trends/{identifier}/video")
    def trend_video(identifier: str):
        return FileResponse(trend_media(identifier, "final_video.mp4"), media_type="video/mp4")

    @app.get("/api/trends/{identifier}/cover")
    def trend_cover(identifier: str):
        return FileResponse(trend_cover_path(identifier), media_type="image/jpeg")

    @app.get("/api/drafts")
    def drafts():
        return store.list("draft", 30)

    @app.get("/api/drafts/{identifier}")
    def draft(identifier: str):
        return require_record("draft", identifier)

    @app.post("/api/drafts", status_code=202)
    def generate(body: GenerateInput):
        acct = account()
        if body.mode == "live":
            require_capability("script")
        reference = require_record("analysis", body.analysisId) if body.analysisId else None
        return jobs.submit("script", lambda update: store.put("draft", engine.generate(body, acct, reference, update)))

    @app.patch("/api/drafts/{identifier}")
    def update_draft(identifier: str, body: DraftUpdate):
        if not body.script.scenes or not body.script.caption.strip() or len(body.script.scenes) > 30:
            raise HTTPException(400, "剧本需要 1 到 30 个分镜以及发布文案")
        with store.lock:
            current = require_record("draft", identifier)
            if draft_busy(identifier):
                raise HTTPException(409, "视频生成期间不可修改剧本")
            if current["revision"] != body.revision:
                raise HTTPException(409, "草稿已在其他页面更新，请重新载入后编辑")
            return store.patch("draft", identifier, {"script": body.script.model_dump(), "revision": body.revision + 1,
                                                    "video": None, "prompts": None})

    @app.post("/api/drafts/{identifier}/video", status_code=202)
    def video(identifier: str):
        require_capability("video")
        with store.lock:
            current = require_record("draft", identifier)
            if draft_busy(identifier):
                raise HTTPException(409, "该草稿已有视频任务，请等待任务完成")
            directory = store.directory / "videos" / identifier
            def operation(update):
                changes = engine.render_video(current, directory, update)
                return store.patch("draft", identifier, changes)
            return jobs.submit("video", operation, {"draftId": identifier})

    @app.get("/api/drafts/{identifier}/video-file")
    def video_file(identifier: str):
        current = require_record("draft", identifier)
        target = store.directory / "videos" / identifier / "final_video.mp4"
        if not current.get("video") or not target.is_file():
            raise HTTPException(404, "成片尚未生成")
        return FileResponse(target, media_type="video/mp4")

    @app.post("/api/drafts/{identifier}/queue", status_code=201)
    def queue(identifier: str, body: QueueInput):
        current = require_record("draft", identifier)
        if not current.get("video"):
            raise HTTPException(409, "请先生成成片，或导出当前文案包")
        with store.lock:
            record = {"id": identifier, "draftId": identifier, "platforms": body.platforms,
                      "revision": current["revision"], "status": "awaiting_authorization",
                      "message": "已保存到待发布队列；平台尚未授权，未执行真实发布。", "createdAt": timestamp()}
            return store.put("queue", record)

    @app.post("/api/drafts/{identifier}/export")
    def export(identifier: str):
        current = require_record("draft", identifier)
        script = Script.model_validate(current["script"])
        directory = store.directory / "exports" / new_id()
        directory.mkdir(parents=True)
        if current.get("video"):
            publisher.generate_publish_package(store.directory / "videos" / identifier / "final_video.mp4",
                                               script, directory, current["account"]["profile"]["platforms"][0])
        (directory / "caption.txt").write_text(script.caption, encoding="utf-8")
        (directory / "hashtags.txt").write_text("\n".join("#" + tag.lstrip("#") for tag in script.hashtags), encoding="utf-8")
        (directory / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
        if current.get("prompts"):
            (directory / "video-prompts.json").write_text(
                json.dumps(current["prompts"], ensure_ascii=False, indent=2), encoding="utf-8")
        if current.get("analysisId"):
            analysis = store.get("analysis", current["analysisId"])
            if analysis:
                (directory / "reverse-analysis.json").write_text(
                    json.dumps({"reverse": analysis.get("reverse"), "promptPack": analysis.get("promptPack")},
                               ensure_ascii=False, indent=2), encoding="utf-8")
        (directory / "metadata.json").write_text(json.dumps({
            "draftId": identifier, "revision": current["revision"], "mode": current["mode"],
            "containsVideo": bool(current.get("video")), "platforms": current["account"]["profile"]["platforms"],
            "published": False,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        archive = directory / "creatoros-publish.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for file in directory.iterdir():
                if file != archive:
                    output.write(file, file.name)
        store.put("export", {"id": directory.name, "createdAt": timestamp()})
        return {"url": f"/api/exports/{directory.name}", "containsVideo": bool(current.get("video"))}

    @app.get("/api/exports/{identifier}")
    def export_file(identifier: str):
        record = require_record("export", identifier)
        return FileResponse(store.directory / "exports" / record["id"] / "creatoros-publish.zip",
                            media_type="application/zip", filename="creatoros-publish.zip")

    @app.get("/api/jobs/{identifier}")
    def job(identifier: str):
        return require_record("job", identifier)

    @app.get("/api/jobs")
    def list_jobs():
        return store.list("job")

    @app.get("/api/queue")
    def list_queue():
        return store.list("queue")

    static_dir = Path(os.getenv("CREATOROS_STATIC_DIR", ROOT.parent / "frontend" / "dist"))
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app


app = create_app()
