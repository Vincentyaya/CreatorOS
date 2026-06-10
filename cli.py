"""CLI:AI视频爆款复制完整流程。

典型用法:
  # 全流程(从平台URL)
  python -m cli run-url "https://www.douyin.com/video/xxx"

  # 全流程(从本地视频)
  python -m cli run path/to/video.mp4

  # 单步重跑(改完中间产物后,从某步继续)
  python -m cli subtitles path/to/video.mp4   # 仅出字幕
  python -m cli reverse                         # 用最近run重跑逆向
  python -m cli script                          # 重跑仿写(会读最新的逆向产物)
  python -m cli prompts --target kling          # 重跑生成prompt
  python -m cli generate                        # 生成视频
  python -m cli publish                         # 生成发布包

可干预:每步产物在 runs/<id>/0X_*.json,手动改完再跑下一步即可。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from pipeline import reverse_prompt, script_writer, subtitles as subs, video_prompt_builder, video_generator, publisher
from pipeline.models import GenerationResult, ReversePrompt, Script, Subtitles, VideoPrompts
from pipeline.run import Run, latest_run
from pipeline.video_downloader import download_with_fallback

app = typer.Typer(add_completion=False, help="AI 视频爆款复制完整流程")
console = Console()


def _get_run(video: Optional[Path]) -> Run:
    """有视频参数就新建 run,否则取最近的 run。"""
    if video:
        if not video.exists():
            console.print(f"[red]找不到视频文件: {video}[/red]")
            raise typer.Exit(1)
        return Run.create(video)
    return latest_run()


@app.command(name="subtitles")
def cmd_subtitles(video: Path):
    """阶段1:提取字幕。"""
    run = _get_run(video)
    console.print(f"[cyan]提取字幕[/cyan] → {run.run_id}")
    result = subs.transcribe(run.source)
    path = run.save("subtitles", result)
    console.print(f"语言: {result.language},片段: {len(result.segments)} 条")
    console.print(f"[green]已保存[/green] {path}")


@app.command(name="reverse")
def cmd_reverse(video: Optional[Path] = typer.Argument(None)):
    """阶段2:逆向 prompt(用最近run或新视频)。"""
    run = _get_run(video)
    console.print(f"[cyan]逆向 prompt[/cyan] → {run.run_id}")
    subtitles = run.load("subtitles", Subtitles) if run.has("subtitles") else None
    result = reverse_prompt.reverse(run.source, subtitles)
    path = run.save("reverse_prompt", result)
    console.print(Panel(result.summary, title="逆向概括"))
    console.print(f"分镜: {len(result.shots)} 个")
    console.print(f"[green]已保存[/green] {path}")


@app.command(name="script")
def cmd_script(account: Optional[Path] = typer.Option(None, help="账号配置json")):
    """阶段3:仿写剧本(读最近run的逆向产物)。"""
    run = latest_run()
    console.print(f"[cyan]仿写剧本[/cyan] → {run.run_id}")
    reverse = run.load("reverse_prompt", ReversePrompt)
    subtitles = run.load("subtitles", Subtitles) if run.has("subtitles") else None
    acct = script_writer.load_account(account)
    result = script_writer.rewrite(reverse, subtitles, acct)
    path = run.save("script", result)
    console.print(Panel(f"{result.title}\n\n钩子: {result.hook}", title="仿写剧本"))
    console.print(f"分镜: {len(result.scenes)} 个")
    console.print(f"[green]已保存[/green] {path}")


@app.command(name="prompts")
def cmd_prompts(target: str = typer.Option("generic", help="目标视频模型,如 kling/jimeng/runway")):
    """阶段4:生成新视频 prompt(读最近run的剧本+逆向)。"""
    run = latest_run()
    console.print(f"[cyan]生成视频 prompt[/cyan] → {run.run_id}")
    script = run.load("script", Script)
    reverse = run.load("reverse_prompt", ReversePrompt)
    result = video_prompt_builder.build(script, reverse, target_model=target)
    path = run.save("video_prompts", result)
    for clip in result.clips:
        console.print(f"[yellow]分镜{clip.index}[/yellow] ({clip.duration_sec}s): {clip.prompt}")
    console.print(f"[green]已保存[/green] {path}")


@app.command(name="generate")
def cmd_generate(
    ratio: str = typer.Option("9:16", help="画幅(16:9/9:16/4:3/3:4)"),
    duration: str = typer.Option("～30s", help="时长(～15s/～30s/40～60s)"),
    reference_video: Optional[str] = typer.Option(None, help="参考视频公网URL(爆款复刻)"),
    timeout: int = typer.Option(1200, help="轮询超时(秒)"),
):
    """阶段5:生成视频(读最近run的video_prompts,调用小云雀API)。"""
    run = latest_run()
    console.print(f"[cyan]生成视频[/cyan] → {run.run_id}")
    prompts = run.load("video_prompts", VideoPrompts)
    output_dir = run.dir / "videos"
    result = video_generator.generate_videos(
        prompts,
        output_dir,
        ratio=ratio,
        duration=duration,
        reference_video_url=reference_video,
        timeout=timeout,
    )
    path = run.save("generation_result", result)
    console.print(f"[green]已保存[/green] {path}")


@app.command(name="publish")
def cmd_publish(
    platform: str = typer.Option("douyin", help="目标平台(douyin/xiaohongshu)"),
):
    """阶段6:生成发布包(读最近run的生成结果+剧本,导出视频+文案)。"""
    run = latest_run()
    console.print(f"[cyan]生成发布包[/cyan] → {run.run_id}")

    # 读取生成结果
    gen_result = run.load("generation_result", GenerationResult)
    if not gen_result.videos or gen_result.videos[0].status != "done":
        console.print("[red]未找到生成成功的视频,请先运行 generate 命令[/red]")
        raise typer.Exit(1)

    video_path = Path(gen_result.videos[0].local_path)
    if not video_path.exists():
        console.print(f"[red]视频文件不存在: {video_path}[/red]")
        raise typer.Exit(1)

    # 读取剧本
    script = run.load("script", Script)

    # 生成发布包
    output_dir = run.dir / "publish_package"
    metadata = publisher.generate_publish_package(video_path, script, output_dir, platform)

    console.print(Panel(
        f"标题: {metadata['title']}\n"
        f"话题: {' '.join(metadata['hashtags'])}\n"
        f"平台: {metadata['platform']}\n\n"
        f"发布包已生成: {output_dir}\n"
        f"[dim]请查看 发布指南.md 了解发布步骤[/dim]",
        title="[green]发布包已生成[/green]",
    ))


@app.command(name="download")
def cmd_download(
    url: str = typer.Argument(..., help="视频URL(抖音/小红书分享链接)"),
    output: Optional[Path] = typer.Option(None, help="输出路径,留空则自动命名"),
):
    """下载平台视频(抖音/小红书等,自动去水印)。"""
    console.print(f"[cyan]下载视频[/cyan] {url}")

    try:
        result = download_with_fallback(url, output)
        console.print(f"[green]下载完成[/green] {result}")
        console.print(f"\n现在可以运行: [yellow]python -m cli run {result}[/yellow]")
    except Exception as e:
        console.print(f"[red]下载失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="run-url")
def cmd_run_url(
    url: str = typer.Argument(..., help="视频URL(抖音/小红书分享链接)"),
    account: Optional[Path] = typer.Option(None, help="账号配置json"),
    target: str = typer.Option("generic", help="目标视频模型"),
    platform: str = typer.Option("douyin", help="发布平台(douyin/xiaohongshu)"),
    skip_generate: bool = typer.Option(False, help="跳过视频生成"),
):
    """完整流程:下载视频 → 全流程处理 → 生成发布包。"""
    # 1. 下载视频
    console.print(Panel(f"开始完整流程\n下载URL: {url}", title="完整流程"))
    console.print("[cyan]1/7 下载视频...[/cyan]")

    try:
        video_path = download_with_fallback(url)
        console.print(f"[green]下载完成[/green] {video_path}")
    except Exception as e:
        console.print(f"[red]下载失败: {e}[/red]")
        raise typer.Exit(1)

    # 2-5. 运行标准流程
    run = Run.create(video_path)
    console.print(f"run: {run.run_id}")

    console.print("[cyan]2/7 提取字幕...[/cyan]")
    subtitles = subs.transcribe(run.source)
    run.save("subtitles", subtitles)

    console.print("[cyan]3/7 逆向 prompt...[/cyan]")
    reverse = reverse_prompt.reverse(run.source, subtitles)
    run.save("reverse_prompt", reverse)

    console.print("[cyan]4/7 仿写剧本...[/cyan]")
    acct = script_writer.load_account(account)
    script = script_writer.rewrite(reverse, subtitles, acct)
    run.save("script", script)

    console.print("[cyan]5/7 生成视频 prompt...[/cyan]")
    prompts = video_prompt_builder.build(script, reverse, target_model=target)
    run.save("video_prompts", prompts)

    if not skip_generate:
        # 6. 生成视频
        console.print("[cyan]6/7 生成视频...[/cyan]")
        output_dir = run.dir / "videos"
        gen_result = video_generator.generate_videos(prompts, output_dir)
        run.save("generation_result", gen_result)

        # 7. 生成发布包
        console.print("[cyan]7/7 生成发布包...[/cyan]")
        if gen_result.videos and gen_result.videos[0].status == "done":
            video_path = Path(gen_result.videos[0].local_path)
            output_dir = run.dir / "publish_package"
            metadata = publisher.generate_publish_package(video_path, script, output_dir, platform)

            console.print(Panel(
                f"完成!产物在 runs/{run.run_id}/\n"
                f"标题: {script.title}\n"
                f"分镜: {len(prompts.clips)} 个\n"
                f"发布包: {output_dir}\n\n"
                f"[dim]查看 发布指南.md 了解发布步骤[/dim]",
                title="[green]完整流程完成[/green]",
            ))
        else:
            console.print("[yellow]视频生成失败,请检查日志[/yellow]")
    else:
        console.print(Panel(
            f"完成!产物在 runs/{run.run_id}/\n"
            f"标题: {script.title}\n分镜: {len(prompts.clips)} 个\n\n"
            f"[dim]运行 python -m cli generate 生成视频[/dim]",
            title="[green]流程完成(跳过生成)[/green]",
        ))


@app.command(name="run")
def cmd_run(
    video: Path,
    account: Optional[Path] = typer.Option(None, help="账号配置json"),
    target: str = typer.Option("generic", help="目标视频模型"),
    skip_subtitles: bool = typer.Option(False, help="跳过字幕(无语音视频)"),
):
    """全流程:字幕 → 逆向 → 仿写 → 生成prompt。"""
    run = _get_run(video)
    console.print(Panel(f"开始处理: {video.name}\nrun: {run.run_id}", title="全流程"))

    subtitles = None
    if not skip_subtitles:
        console.print("[cyan]1/4 提取字幕...[/cyan]")
        subtitles = subs.transcribe(run.source)
        run.save("subtitles", subtitles)

    console.print("[cyan]2/4 逆向 prompt...[/cyan]")
    reverse = reverse_prompt.reverse(run.source, subtitles)
    run.save("reverse_prompt", reverse)

    console.print("[cyan]3/4 仿写剧本...[/cyan]")
    acct = script_writer.load_account(account)
    script = script_writer.rewrite(reverse, subtitles, acct)
    run.save("script", script)

    console.print("[cyan]4/4 生成视频 prompt...[/cyan]")
    prompts = video_prompt_builder.build(script, reverse, target_model=target)
    run.save("video_prompts", prompts)

    console.print(Panel(
        f"完成!产物在 runs/{run.run_id}/\n"
        f"标题: {script.title}\n分镜: {len(prompts.clips)} 个\n\n"
        f"[dim]改任意中间产物后,可单步重跑后续阶段。[/dim]",
        title="[green]全流程完成[/green]",
    ))


if __name__ == "__main__":
    app()
