"""Build the fixed, locally playable trend-video library and matching covers."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.pipeline.composed_video import render


SCRIPTS = {
    "bili-cat-talk": [
        ("铁柱", "期待", "我健身一小时，奖励自己一杯全糖奶茶，不过分吧？"),
        ("甜甜", "冷静", "不过分。你只是把刚消耗的热量，亲自接回了家。"),
    ],
    "bili-cat-story": [
        ("铁柱", "沮丧", "今天什么都没做好，是不是该放弃了？"),
        ("甜甜", "温柔", "偶尔走得慢，不代表走错了。先吃饭，明天再出发。"),
    ],
    "bili-pet-fusion": [
        ("铁柱", "兴奋", "如果柴犬和企鹅合体，会变成什么？"),
        ("甜甜", "吐槽", "会变成一只走两步就想下班的圆滚滚同事。"),
    ],
    "douyin-pet-talk-demo": [
        ("铁柱", "认真", "猫狗委员会今天研究：人类为什么不想上班？"),
        ("甜甜", "冷漠", "因为他们没有尾巴，却每天都在替老板摇。"),
    ],
    "douyin-pet-education-demo": [
        ("铁柱", "好奇", "为什么越怕做不好，越容易一直拖延？"),
        ("甜甜", "讲解", "这叫完美主义拖延。先完成一个小版本，大脑才肯继续。"),
    ],
    "xhs-pet-healing-demo": [
        ("铁柱", "关心", "你今天回家一句话都没说，是不是受委屈了？"),
        ("甜甜", "温柔", "不用马上振作。先让我陪你安静坐一会儿。"),
    ],
    "xhs-pet-knowledge-demo": [
        ("甜甜", "讲解", "学习别一口气硬撑两小时，先专注二十五分钟。"),
        ("铁柱", "恍然大悟", "我懂了，休息五分钟不是偷懒，是给大脑充电！"),
    ],
    "kuaishou-pet-family-demo": [
        ("铁柱", "告状", "甜甜又把杯子推下桌了，家里到底谁管她？"),
        ("甜甜", "淡定", "纠正一下，这个家归我管，包括你。"),
    ],
    "shipinhao-pet-health-demo": [
        ("铁柱", "认真", "坐了一整天，腰酸背痛怎么办？"),
        ("甜甜", "提醒", "先起来走五分钟。身体需要活动，不需要你继续收藏养生文章。"),
    ],
}


def main():
    catalog = json.loads((ROOT / "backend" / "catalog.json").read_text(encoding="utf-8"))
    titles = {item["id"]: item["title"] for item in catalog["videos"]}
    output = ROOT / "backend" / "demo_media"
    characters = [
        {"id": "tiantian", "source": "library", "name": "甜甜", "emoji": "", "accent": "#eef2ff", "img": "/avatars/tiantian.png"},
        {"id": "tiezhu", "source": "library", "name": "铁柱", "emoji": "", "accent": "#fde8c8", "img": "/avatars/tiezhu.png"},
    ]
    for identifier, lines in SCRIPTS.items():
        directory = output / identifier
        draft = {
            "characters": characters,
            "script": {"scenes": [
                {"index": index + 1, "speaker": speaker, "emotion": emotion, "narration": line,
                 "on_screen_text": line, "visual": "萌宠角色对镜头说话"}
                for index, (speaker, emotion, line) in enumerate(lines)
            ]},
        }
        render(draft, directory, ROOT / "backend" / "runtime")
        shutil.copyfile(directory / "compose" / "frame-00.jpg", directory / "cover.jpg")
        print(f"{identifier}: {titles[identifier]}")


if __name__ == "__main__":
    main()
