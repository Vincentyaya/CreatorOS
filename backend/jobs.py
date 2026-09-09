from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from .pipeline import config
from .store import new_id, timestamp


def safe_error(error):
    text = str(error)
    for secret in (
        config.QWEN_API_KEY, config.IMAGE_API_KEY, config.WAN_VIDEO_API_KEY,
        config.JIMENG_ACCESS_KEY_ID, config.JIMENG_SECRET_ACCESS_KEY,
        config.DOUYIN_CLIENT_KEY, config.DOUYIN_CLIENT_SECRET, config.DOUYIN_ACCESS_TOKEN,
    ):
        if secret:
            text = text.replace(secret, "[redacted]")
    return text[:900]


class Jobs:
    def __init__(self, store):
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="creatoros")
        self.slots = threading.BoundedSemaphore(6)
        for job in store.list("job", 10000):
            if job["status"] in ("queued", "running"):
                store.patch("job", job["id"], {"status": "failed", "error": "服务重启，任务已中断。请确认上游任务状态后重试。", "stage": "已中断"})

    def submit(self, kind, operation, metadata=None):
        if not self.slots.acquire(blocking=False):
            raise ValueError("任务队列已满，请稍后重试")
        job = self.store.put("job", {
            "id": new_id(), "kind": kind, "status": "queued", "stage": "等待处理",
            "createdAt": timestamp(), "updatedAt": timestamp(), "result": None, "error": None,
            **(metadata or {}),
        })

        def execute():
            try:
                self.store.patch("job", job["id"], {"status": "running"})
                result = operation(lambda stage: self.store.patch("job", job["id"], {"stage": stage}))
                self.store.patch("job", job["id"], {"status": "completed", "stage": "已完成", "result": result})
            except Exception as error:
                self.store.patch("job", job["id"], {"status": "failed", "stage": "失败", "error": safe_error(error)})
            finally:
                self.slots.release()

        self.pool.submit(execute)
        return job
