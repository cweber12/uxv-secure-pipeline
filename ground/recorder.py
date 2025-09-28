# ground/recorder.py
# JSONL recorder for telemetry and detections, with optional MDM ingest on close
from __future__ import annotations
import os, json, pathlib, time, logging
from typing import TextIO, Dict, Any, Optional

log = logging.getLogger(__name__)

# soft dependency; recorder still works if this module is missing
try:
    from . import mdm_client
except Exception:  
    mdm_client = None

class JsonlRecorder:
    def __init__(
        self,
        root: pathlib.Path,
        mission_id: Optional[str] = None,
        ingest_on_close_flag: Optional[bool] = None,
        mdm_url: Optional[str] = None,
        mdm_api_key: Optional[str] = None,
    ):
        self.root = root
        self.mission_id = mission_id or time.strftime("mission-%Y%m%d-%H%M%S")
        self.dir = self.root / self.mission_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, TextIO] = {}

        # env fallbacks
        if ingest_on_close_flag is None:
            ingest_on_close_flag = os.getenv("MDM_INGEST_ON_CLOSE", "1") != "0"
        self.ingest_on_close = ingest_on_close_flag

        self.mdm_url = mdm_url or os.getenv("MDM_URL")
        self.mdm_api_key = mdm_api_key or os.getenv("MDM_API_KEY")

        log.debug(
            "[recorder] mission_id=%s dir=%s ingest_on_close=%s mdm_url=%s",
            self.mission_id, self.dir, self.ingest_on_close, self.mdm_url
        )

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

    # Close all open files and (optionally) ingest the mission to MDM
    def close(self) -> None:
        for f in self._files.values():
            try:
                f.close()
            except Exception:
                pass
        self._files.clear()

        if not self.ingest_on_close:
            log.info("[recorder] ingest_on_close disabled; skipping MDM ingest")
            return

        if not self.mdm_url:
            log.info("[recorder] MDM_URL not set; skipping MDM ingest")
            return

        if mdm_client is None:
            log.warning("[recorder] mdm_client module not available; skipping MDM ingest")
            return

        try:
            ok, info = mdm_client.ingest_mission_dir(
                mission_dir=self.dir,
                mission_id=self.mission_id,
                mdm_url=self.mdm_url,
                api_key=self.mdm_api_key,
            )
            if ok:
                log.info("[recorder] MDM ingest complete: %s", info)
            else:
                log.warning("[recorder] MDM ingest failed: %s", info)
        except Exception as e:  # never crash the server on ingest problems
            log.exception("[recorder] MDM ingest raised: %s", e)

