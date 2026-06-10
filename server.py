"""FastAPI 后端:把 pipeline 各阶段暴露为 REST API,供前端调用。"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from pipeline import reverse_prompt, script_writer, subtitles as subs, video_prompt_builder, video_generator, publisher
from pipeline.models import GenerationResult, ReversePrompt, Script, Subtitles, VideoPrompts
from pipeline.run import Run, latest_run, RUNS_DIR
from pipeline.video_downloader import download_with_fallback
from pipeline.config import ROOT

app = FastAPI(title="CreatorOS - AI 视频爆款复制")

# 静态文件:前端页面
FRONTEND_DIR = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------- 请求/响应模型 ----------
class UrlInput(BaseModel):
    url: str
    platform: str = "douyin"
    target_model: str = "generic"
    skip_generate: bool = False
    ratio: str = "9:16"
    duration: str = "~30s"


class StageInput(BaseModel):
    run_id: str
    target_model: str = "generic"
    platform: str = "douyin"
    ratio: str = "9:16"
    duration: str = "~30s"
    reference_video_url: Optional[str] = None


class UpdateStageInput(BaseModel):
    run_id: str
    stage: str
    data: dict


# ---------- 工具函数 ----------
def _run_to_dict(run: Run) -> dict:
    """把一个 run 的状态汇总成 dict。"""
    meta_path = run.dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    stages = {}
    for stage_key, filename in {
        "subtitles": "01_subtitles.json",
        "reverse_prompt": "02_reverse_prompt.json",
        "script": "03_script.json",
        "video_prompts": "04_video_prompts.json",
        "generation_result": "05_generation_result.json",
    }.items():
        fpath = run.dir / filename
        if fpath.exists():
            stages[stage_key] = json.loads(fpath.read_text(encoding="utf-8"))
        else:
            stages[stage_key] = None

    # 检查发布包
    publish_dir = run.dir / "publish_package"
    has_publish = publish_dir.exists() and (publish_dir / "metadata.json").exists()
    publish_meta = None
    if has_publish:
        publish_meta = json.loads((publish_dir / "metadata.json").read_text(encoding="utf-8"))

    return {
        "run_id": run.run_id,
        "meta": meta,
        "stages": stages,
        "has_publish_package": has_publish,
        "publish_metadata": publish_meta,
    }


# ---------- API 路由 ----------
@app.get("/")
async def index():
    """前端首页。"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/runs")
async def list_runs():
    """列出所有 run。"""
    if not RUNS_DIR.exists():
        return []
    runs = []
    for d in sorted(RUNS_DIR.iterdir(), reverse=True):
        if d.is_dir() and (d / "meta.json").exists():
            run = Run(d.name)
            runs.append(_run_to_dict(run))
    return runs


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """获取单个 run 详情。"""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(404, f"Run {run_id} 不存在")
    return _run_to_dict(Run(run_id))


@app.post("/api/run-url")
async def run_from_url(background_tasks: BackgroundTasks, body: UrlInput):
    """从 URL 开始完整流程(异步执行)。"""
    # 先创建 run 目录
    run_id = f"url_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "meta.json").write_text(json.dumps({
        "source_url": body.url,
        "platform": body.platform,
        "target_model": body.target_model,
        "status": "running",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 异步执行 pipeline
    background_tasks.add_task(_run_pipeline_from_url, run_id, body)
    return {"run_id": run_id, "status": "started"}


def _update_progress(run_dir: Path, step: str, status: str = "running"):
    """更新进度到 meta.json。"""
    meta_path = run_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = status
        meta["current_step"] = step
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_pipeline_from_url(run_id: str, body: UrlInput):
    """后台执行完整 pipeline。"""
    run_dir = RUNS_DIR / run_id
    try:
        # 1. 下载视频
        _update_progress(run_dir, "downloading")
        video_path = download_with_fallback(body.url)
        _update_progress(run_dir, "downloading_done")

        # 用标准 Run 管理后续
        run = Run(run_id)
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        meta["source"] = str(video_path.resolve())
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. 字幕
        _update_progress(run_dir, "transcribing")
        subtitles = subs.transcribe(video_path)
        run.save("subtitles", subtitles)

        # 3. 逆向
        _update_progress(run_dir, "reversing")
        reverse = reverse_prompt.reverse(video_path, subtitles)
        run.save("reverse_prompt", reverse)

        # 4. 仿写
        _update_progress(run_dir, "scripting")
        acct = script_writer.load_account()
        script = script_writer.rewrite(reverse, subtitles, acct)
        run.save("script", script)

        # 5. 生成 prompt
        _update_progress(run_dir, "building_prompts")
        prompts = video_prompt_builder.build(script, reverse, target_model=body.target_model)
        run.save("video_prompts", prompts)

        if not body.skip_generate:
            # 6. 生成视频
            _update_progress(run_dir, "generating_video")
            output_dir = run.dir / "videos"
            gen_result = video_generator.generate_videos(
                prompts, output_dir,
                ratio=body.ratio if hasattr(body, 'ratio') else "9:16",
                duration=body.duration if hasattr(body, 'duration') else "~30s",
            )
            run.save("generation_result", gen_result)

            # 7. 发布包
            _update_progress(run_dir, "publishing")
            if gen_result.videos and gen_result.videos[0].status == "done":
                video_file = Path(gen_result.videos[0].local_path)
                publisher.generate_publish_package(
                    video_file, script, run.dir / "publish_package", body.platform
                )

        _update_progress(run_dir, "done", "done")

    except Exception as e:
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        meta["status"] = "failed"
        meta["error"] = str(e)
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


@app.post("/api/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """上传本地视频,创建 run 并执行全流程。"""
    # 保存上传文件
    upload_dir = RUNS_DIR / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / file.filename
    with video_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    run_id = f"upload_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "meta.json").write_text(json.dumps({
        "source": str(video_path.resolve()),
        "status": "running",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    background_tasks.add_task(_run_pipeline_from_file, run_id, video_path)
    return {"run_id": run_id, "status": "started"}


def _run_pipeline_from_file(run_id: str, video_path: Path):
    """后台执行 pipeline(从本地文件)。"""
    run_dir = RUNS_DIR / run_id
    try:
        run = Run(run_id)

        subtitles = subs.transcribe(video_path)
        run.save("subtitles", subtitles)

        reverse = reverse_prompt.reverse(video_path, subtitles)
        run.save("reverse_prompt", reverse)

        acct = script_writer.load_account()
        script = script_writer.rewrite(reverse, subtitles, acct)
        run.save("script", script)

        prompts = video_prompt_builder.build(script, reverse)
        run.save("video_prompts", prompts)

        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        meta["status"] = "done"
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    except Exception as e:
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        meta["status"] = "failed"
        meta["error"] = str(e)
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- 单步执行 ----------
@app.post("/api/stage/subtitles")
async def run_subtitles(body: StageInput):
    """执行字幕提取阶段。"""
    run = Run(body.run_id)
    video_path = run.source
    result = subs.transcribe(video_path)
    run.save("subtitles", result)
    return result.model_dump()


@app.post("/api/stage/reverse")
async def run_reverse(body: StageInput):
    """执行逆向 prompt 阶段。"""
    run = Run(body.run_id)
    subtitles = run.load("subtitles", Subtitles) if run.has("subtitles") else None
    result = reverse_prompt.reverse(run.source, subtitles)
    run.save("reverse_prompt", result)
    return result.model_dump()


@app.post("/api/stage/script")
async def run_script(body: StageInput):
    """执行仿写剧本阶段。"""
    run = Run(body.run_id)
    reverse = run.load("reverse_prompt", ReversePrompt)
    subtitles = run.load("subtitles", Subtitles) if run.has("subtitles") else None
    acct = script_writer.load_account()
    result = script_writer.rewrite(reverse, subtitles, acct)
    run.save("script", result)
    return result.model_dump()


@app.post("/api/stage/prompts")
async def run_prompts(body: StageInput):
    """执行视频 prompt 生成阶段。"""
    run = Run(body.run_id)
    script = run.load("script", Script)
    reverse = run.load("reverse_prompt", ReversePrompt)
    result = video_prompt_builder.build(script, reverse, target_model=body.target_model)
    run.save("video_prompts", result)
    return result.model_dump()


@app.post("/api/stage/generate")
async def run_generate(body: StageInput):
    """执行视频生成阶段。"""
    run = Run(body.run_id)
    prompts = run.load("video_prompts", VideoPrompts)
    output_dir = run.dir / "videos"
    result = video_generator.generate_videos(
        prompts, output_dir,
        ratio=body.ratio,
        duration=body.duration,
        reference_video_url=body.reference_video_url,
    )
    run.save("generation_result", result)
    return result.model_dump()


@app.post("/api/stage/publish")
async def run_publish(body: StageInput):
    """执行发布包生成阶段。"""
    run = Run(body.run_id)
    gen_result = run.load("generation_result", GenerationResult)
    if not gen_result.videos or gen_result.videos[0].status != "done":
        raise HTTPException(400, "没有生成成功的视频")
    video_path = Path(gen_result.videos[0].local_path)
    script = run.load("script", Script)
    output_dir = run.dir / "publish_package"
    metadata = publisher.generate_publish_package(video_path, script, output_dir, body.platform)
    return metadata


# ---------- 更新中间产物(人工干预) ----------
@app.put("/api/stage")
async def update_stage(body: UpdateStageInput):
    """手动更新某个阶段的产物(人工干预后保存)。"""
    run = Run(body.run_id)
    stage_files = {
        "subtitles": "01_subtitles.json",
        "reverse_prompt": "02_reverse_prompt.json",
        "script": "03_script.json",
        "video_prompts": "04_video_prompts.json",
        "generation_result": "05_generation_result.json",
    }
    if body.stage not in stage_files:
        raise HTTPException(400, f"未知阶段: {body.stage}")
    fpath = run.dir / stage_files[body.stage]
    fpath.write_text(json.dumps(body.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


# ---------- 文件访问 ----------
@app.get("/api/runs/{run_id}/video")
async def get_video(run_id: str):
    """获取生成的视频文件。"""
    video_path = RUNS_DIR / run_id / "videos" / "final_video.mp4"
    if not video_path.exists():
        raise HTTPException(404, "视频不存在")
    return FileResponse(str(video_path), media_type="video/mp4")


@app.get("/api/runs/{run_id}/publish-package")
async def get_publish_package(run_id: str):
    """获取发布包元数据。"""
    pkg_dir = RUNS_DIR / run_id / "publish_package"
    if not pkg_dir.exists():
        raise HTTPException(404, "发布包不存在")
    meta = json.loads((pkg_dir / "metadata.json").read_text(encoding="utf-8"))
    if (pkg_dir / "caption.txt").exists():
        meta["caption_text"] = (pkg_dir / "caption.txt").read_text(encoding="utf-8")
    if (pkg_dir / "hashtags.txt").exists():
        meta["hashtags_text"] = (pkg_dir / "hashtags.txt").read_text(encoding="utf-8")
    return meta


@app.get("/api/account")
async def get_account():
    """获取账号配置。"""
    from pipeline.config import CONFIG_DIR
    acct_path = CONFIG_DIR / "account.json"
    if not acct_path.exists():
        return {}
    return json.loads(acct_path.read_text(encoding="utf-8"))


@app.put("/api/account")
async def update_account(data: dict):
    """更新账号配置。"""
    from pipeline.config import CONFIG_DIR
    acct_path = CONFIG_DIR / "account.json"
    acct_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
