# ground/recorder.py
from __future__ import annotations
import json, pathlib, time
from typing import TextIO, Dict, Any

class JsonlRecorder:
    def __init__(self, root: pathlib.Path, mission_id: str | None = None):
        self.root = root
        self.mission_id = mission_id or time.strftime("mission-%Y%m%d-%H%M%S")
        self.dir = self.root / self.mission_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, TextIO] = {}

    def _open(self, name: str) -> TextIO:
        if name not in self._files:
            self._files[name] = (self.dir / f"{name}.jsonl").open("a", encoding="utf-8")
        return self._files[name]

    def write(self, stream: str, obj: Dict[str, Any]) -> None:
        f = self._open(stream)
        f.write(json.dumps(obj) + "\n")
        f.flush()  # keep data durable for demos

    def close(self) -> None:
        for f in self._files.values():
            try: f.close()
            except: pass
        self._files.clear()
