"""Run 管理:每次处理一个视频是一个 run,各阶段产物落盘到 runs/<id>/。

这是"可干预重跑"的核心:
- 每个阶段从磁盘读上一阶段产物、写自己的产物
- 用户改了任一中间文件(如 02_reverse_prompt.json),后续阶段直接用新内容
- 任一阶段都可单独重跑,不必从头来
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

from .config import RUNS_DIR

T = TypeVar("T", bound=BaseModel)

# 各阶段产物的固定文件名(数字前缀=执行顺序)
STAGE_FILES = {
    "subtitles": "01_subtitles.json",
    "reverse_prompt": "02_reverse_prompt.json",
    "script": "03_script.json",
    "video_prompts": "04_video_prompts.json",
    "generation_result": "05_generation_result.json",
}


class Run:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.dir = RUNS_DIR / run_id
        self.dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls, source: Path) -> "Run":
        """为一个源视频新建 run,id 用 时间戳+文件名。"""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = cls(f"{stamp}_{source.stem}")
        # 记录元信息
        (run.dir / "meta.json").write_text(
            json.dumps(
                {"source": str(source.resolve()), "created": stamp},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return run

    @property
    def source(self) -> Path:
        meta = json.loads((self.dir / "meta.json").read_text(encoding="utf-8"))
        return Path(meta["source"])

    def _path(self, stage: str) -> Path:
        return self.dir / STAGE_FILES[stage]

    def has(self, stage: str) -> bool:
        return self._path(stage).exists()

    def save(self, stage: str, data: BaseModel) -> Path:
        path = self._path(stage)
        path.write_text(
            json.dumps(data.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, stage: str, model: Type[T]) -> T:
        path = self._path(stage)
        if not path.exists():
            raise FileNotFoundError(
                f"阶段 '{stage}' 的产物不存在({path.name})。请先运行该阶段。"
            )
        return model.model_validate_json(path.read_text(encoding="utf-8"))


def latest_run() -> Run:
    """取最近一次 run,方便不带参数重跑后续阶段。"""
    if not RUNS_DIR.exists():
        raise FileNotFoundError("还没有任何 run,请先 ingest 一个视频。")
    dirs = [d for d in RUNS_DIR.iterdir() if d.is_dir()]
    if not dirs:
        raise FileNotFoundError("还没有任何 run,请先 ingest 一个视频。")
    return Run(max(dirs, key=lambda d: d.stat().st_mtime).name)
