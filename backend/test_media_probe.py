import json
import os

import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")
KEY = os.getenv("QWEN_API_KEY", "")
BASE = os.getenv("QWEN_BASE_URL", "")
ROOT = BASE.split("/compatible-mode/v1")[0] + "/api/v1"
print("ROOT:", ROOT)


def post(path, body, async_=False):
    head = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if async_:
        head["X-DashScope-Async"] = "enable"
    try:
        r = requests.post(f"{ROOT}{path}", headers=head, json=body, timeout=120)
        print(f"POST /api/v1{path} model={body.get('model')} -> {r.status_code}")
        try:
            print(json.dumps(r.json(), ensure_ascii=False)[:900])
        except Exception:
            print(r.text[:900])
    except Exception as e:
        print(f"POST {path} ERROR: {e}")
    print("===")


post("/services/aigc/multimodal-generation/generation", {
    "model": "qwen-image-2.0",
    "input": {"messages": [{"role": "user", "content": [{"text": "一只可爱的卡通柴犬头像，扁平3D风格，纯色背景"}]}]},
    "parameters": {"prompt_extend": True, "watermark": False, "n": 1, "size": "1280*1280"},
})

post("/services/aigc/text2image/image-synthesis", {
    "model": "wan2.7-image",
    "input": {"prompt": "一只可爱的卡通柴犬头像，扁平3D风格，纯色背景"},
    "parameters": {"size": "1024*1024", "n": 1},
})

post("/services/aigc/audio/speech-synthesize/speech-synthesis", {
    "model": "qwen-audio-3.0-tts-plus",
    "input": {"text": "今天又是打工的一天。", "voice": "Cherry", "format": "mp3"},
})

post("/services/aigc/multimodal-generation/generation", {
    "model": "qwen-audio-3.0-tts-plus",
    "input": {"messages": [{"role": "user", "content": [{"text": "今天又是打工的一天。"}]}]},
    "parameters": {"voice": "Cherry", "language_type": "Chinese"},
})