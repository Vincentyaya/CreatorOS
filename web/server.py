"""FastAPI 后端:提供 AI 视频爆款复制流程的 API。"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from pipeline.run import Run, latest_run, RUNS_DIR
from pipeline import reverse_prompt, script_writer, subtitles as subs, video_prompt_builder, video_generator, publisher
from pipeline.models import ReversePrompt, Script, Subtitles, VideoPrompts, GenerationResult
from pipeline.video_downloader import download_with_fallback

app = FastAPI(title="AI 视频爆款复制")

# 静态文件
WEB_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


# ============ 数据模型 ============
class RunInfo(BaseModel):
    run_id: str
    source: str
    created: str
    stages: dict[str, bool]  # 各阶段是否完成


class ProcessRequest(BaseModel):
    url: Optional[str] = None
    video_path: Optional[str] = None
    platform: str = "douyin"
    skip_generate: bool = False


# ============ 辅助函数 ============
def get_run_info(run: Run) -> RunInfo:
    """获取 run 的元信息。"""
    meta = json.loads((run.dir / "meta.json").read_text(encoding="utf-8"))
    stages = {
        "subtitles": run.has("subtitles"),
        "reverse_prompt": run.has("reverse_prompt"),
        "script": run.has("script"),
        "video_prompts": run.has("video_prompts"),
        "generation_result": run.has("generation_result"),
    }
    return RunInfo(
        run_id=run.run_id,
        source=meta.get("source", ""),
        created=meta.get("created", ""),
        stages=stages,
    )


# ============ API 路由 ============
@app.get("/")
async def index():
    """首页。"""
    return FileResponse(WEB_DIR / "static" / "index.html")


@app.get("/api/runs")
async def list_runs():
    """列出所有 runs。"""
    if not RUNS_DIR.exists():
        return []
    runs = []
    for d in sorted(RUNS_DIR.iterdir(), reverse=True):
        if d.is_dir() and (d / "meta.json").exists():
            try:
                run = Run(d.name)
                runs.append(get_run_info(run))
            except Exception:
                pass
    return runs


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """获取单个 run 的详情。"""
    run = Run(run_id)
    if not (run.dir / "meta.json").exists():
        raise HTTPException(404, f"Run 不存在: {run_id}")

    result = {"info": get_run_info(run)}

    # 加载各阶段产物
    for stage, model in [
        ("subtitles", Subtitles),
        ("reverse_prompt", ReversePrompt),
        ("script", Script),
        ("video_prompts", VideoPrompts),
        ("generation_result", GenerationResult),
    ]:
        if run.has(stage):
            result[stage] = run.load(stage, model).model_dump()

    return result


@app.get("/api/runs/{run_id}/video")
async def get_video(run_id: str):
    """获取生成的视频文件。"""
    run = Run(run_id)
    if not run.has("generation_result"):
        raise HTTPException(404, "没有生成结果")

    gen = run.load("generation_result", GenerationResult)
    if not gen.videos or gen.videos[0].status != "done":
        raise HTTPException(404, "视频生成失败")

    video_path = Path(gen.videos[0].local_path)
    if not video_path.exists():
        raise HTTPException(404, "视频文件不存在")

    return FileResponse(video_path, media_type="video/mp4")


@app.get("/api/runs/{run_id}/publish")
async def get_publish_package(run_id: str):
    """获取发布包文件列表。"""
    run = Run(run_id)
    publish_dir = run.dir / "publish_package"
    if not publish_dir.exists():
        raise HTTPException(404, "发布包不存在")

    files = []
    for f in publish_dir.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "url": f"/api/runs/{run_id}/publish/{f.name}",
            })
    return files


@app.get("/api/runs/{run_id}/publish/{filename}")
async def get_publish_file(run_id: str, filename: str):
    """获取发布包中的单个文件。"""
    run = Run(run_id)
    file_path = run.dir / "publish_package" / filename
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(file_path)


@app.post("/api/process")
async def process_video(req: ProcessRequest):
    """处理视频:下载 → 字幕 → 逆向 → 仿写 → 生成prompt → 生成视频。"""

    # 1. 获取视频
    if req.url:
        try:
            video_path = download_with_fallback(req.url)
        except Exception as e:
            raise HTTPException(400, f"下载失败: {e}")
    elif req.video_path:
        video_path = Path(req.video_path)
        if not video_path.exists():
            raise HTTPException(400, f"视频文件不存在: {video_path}")
    else:
        raise HTTPException(400, "需要提供 url 或 video_path")

    # 2. 创建 run
    run = Run.create(video_path)

    # 3. 提取字幕
    try:
        subtitles = subs.transcribe(run.source)
        run.save("subtitles", subtitles)
    except Exception as e:
        # 字幕失败不阻塞后续
        subtitles = None

    # 4. 逆向 prompt
    try:
        reverse = reverse_prompt.reverse(run.source, subtitles)
        run.save("reverse_prompt", reverse)
    except Exception as e:
        raise HTTPException(500, f"逆向 prompt 失败: {e}")

    # 5. 仿写剧本
    try:
        acct = script_writer.load_account(None)
        script = script_writer.rewrite(reverse, subtitles, acct)
        run.save("script", script)
    except Exception as e:
        raise HTTPException(500, f"仿写剧本失败: {e}")

    # 6. 生成视频 prompt
    try:
        prompts = video_prompt_builder.build(script, reverse)
        run.save("video_prompts", prompts)
    except Exception as e:
        raise HTTPException(500, f"生成视频 prompt 失败: {e}")

    # 7. 生成视频（可选）
    if not req.skip_generate:
        try:
            output_dir = run.dir / "videos"
            gen_result = video_generator.generate_videos(prompts, output_dir)
            run.save("generation_result", gen_result)

            # 8. 生成发布包
            if gen_result.videos and gen_result.videos[0].status == "done":
                video_path = Path(gen_result.videos[0].local_path)
                publish_dir = run.dir / "publish_package"
                publisher.generate_publish_package(video_path, script, publish_dir, req.platform)
        except Exception as e:
            # 生成失败不阻塞返回
            pass

    return get_run_info(run)


@app.post("/api/runs/{run_id}/generate")
async def generate_video(run_id: str, platform: str = "douyin"):
    """对已有 run 生成视频和发布包。"""
    run = Run(run_id)

    if not run.has("video_prompts"):
        raise HTTPException(400, "缺少 video_prompts，请先完成前面的步骤")

    prompts = run.load("video_prompts", VideoPrompts)
    script = run.load("script", Script) if run.has("script") else None

    # 生成视频
    output_dir = run.dir / "videos"
    gen_result = video_generator.generate_videos(prompts, output_dir)
    run.save("generation_result", gen_result)

    # 生成发布包
    if gen_result.videos and gen_result.videos[0].status == "done" and script:
        video_path = Path(gen_result.videos[0].local_path)
        publish_dir = run.dir / "publish_package"
        publisher.generate_publish_package(video_path, script, publish_dir, platform)

    return get_run_info(run)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
