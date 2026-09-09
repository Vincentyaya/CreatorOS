from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid4().hex


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "creatoros.sqlite3"
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT NOT NULL, updated TEXT NOT NULL, PRIMARY KEY(kind,id))")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def get(self, kind, identifier):
        with self.connect() as db:
            row = db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind, limit=50):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM records WHERE kind=? ORDER BY updated DESC LIMIT ?", (kind, limit)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put(self, kind, value):
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body, updated=excluded.updated",
                       (kind, value["id"], json.dumps(value, ensure_ascii=False), timestamp()))
        return value

    def patch(self, kind, identifier, changes):
        with self.lock:
            current = self.get(kind, identifier)
            if current is None:
                raise KeyError(identifier)
            current.update(changes)
            current["updatedAt"] = timestamp()
            return self.put(kind, current)

    def delete(self, kind, identifier):
        with self.lock, self.connect() as db:
            cursor = db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, identifier))
            return cursor.rowcount > 0
