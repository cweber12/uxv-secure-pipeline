# ground/recorder.py
# JSONL recorder for telemetry and detections
from __future__ import annotations
import json, pathlib, time
from typing import TextIO, Dict, Any

# Simple JSONL recorder that creates a new directory for each "mission"
class JsonlRecorder:

    # root dir where missions are created
    def __init__(self, root: pathlib.Path, mission_id: str | None = None):
        self.root = root
        self.mission_id = mission_id or time.strftime("mission-%Y%m%d-%H%M%S")
        self.dir = self.root / self.mission_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, TextIO] = {}

    # Open (or create) a file for the given stream name
    def _open(self, name: str) -> TextIO:
        if name not in self._files:
            self._files[name] = (self.dir / f"{name}.jsonl").open("a", encoding="utf-8")
        return self._files[name]

    # Write a JSON object to the given stream (creates file if needed)
    def write(self, stream: str, obj: Dict[str, Any]) -> None:
        f = self._open(stream)
        f.write(json.dumps(obj) + "\n")
        f.flush()  # keep data durable for demos

    # Close all open files
    def close(self) -> None:
        for f in self._files.values():
            try: f.close()
            except: pass
        self._files.clear()
