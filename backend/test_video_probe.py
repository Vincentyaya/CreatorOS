import json
import os
import sys

import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

KEY = os.getenv("QWEN_API_KEY", "")
BASE = os.getenv("QWEN_BASE_URL", "")
print("BASE:", BASE)
print("KEY prefix:", KEY[:12], "len", len(KEY))

if "/compatible-mode/v1" in BASE:
    ROOT = BASE.split("/compatible-mode/v1")[0]
else:
    ROOT = BASE.rstrip("/")
print("ROOT:", ROOT)


def get(path):
    r = requests.get(f"{ROOT}{path}", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
    print("GET", path, "->", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False)[:1500])
    except Exception:
        print(r.text[:1500])
    print("---")


def post(path, body):
    head = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    r = requests.post(f"{ROOT}{path}", headers=head, json=body, timeout=60)
    print("POST", path, "->", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False)[:1500])
    except Exception:
        print(r.text[:1500])
    print("---")


get("/compatible-mode/v1/models")

models = ["wan3.0-video", "wan3.0-video-prime", "wan2.7-t2v", "wan2.7-t2v-2026-06-12",
          "wan2.6-t2v", "wan2.2-t2v-plus", "wan2.1-t2v-turbo", "wan2.1-t2v-plus"]

for m in models:
    post("/services/aigc/video-generation/video-synthesis", {
        "model": m,
        "input": {"prompt": "一只可爱的卡通柴犬在草地上奔跑，阳光明媚，竖屏9:16，高清"},
        "parameters": {"resolution": "720P", "ratio": "9:16", "duration": 5},
    })