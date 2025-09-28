# ground/mdm_client.py
from __future__ import annotations
import os, json, pathlib, time, logging, mimetypes
from typing import Optional, Tuple

log = logging.getLogger(__name__)

try: 
    import requests
except ImportError:
    raise ImportError("mdm_client requires the 'requests' package; please install it via pip")

# Config via env (override in tests/CI as needed)
MDM_URL = os.getenv("MDM_URL", "http://127.0.0.1:8080/ingest")
MDM_API_KEY = os.getenv("MDM_API_KEY", "")

def _detect_content_type(p: pathlib.Path, default: str = "application/octet-stream") -> str:
    # Prefer correct JSONL type
    if p.suffix.lower() in {".jsonl", ".ndjson"}:
        return "application/x-ndjson"
    ct, _ = mimetypes.guess_type(str(p))
    return ct or default

def ingest_path(
    mission_id: str,
    path: pathlib.Path,
    *,
    logical_name: str | None = None,
    object_type: str = "",
    tags: dict | None = None,
    content_type: str | None = None,
    sensor: str = "",
    platform: str = "",
    classification: str = "UNCLASS",
    pipeline_run_id: str = "",
    timeout: float = 30.0,
) -> dict:
    """
    Upload a file to the MDM /ingest endpoint with metadata header.
    Raises requests.HTTPError for non-2xx to let caller decide how to handle.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))

    ln = logical_name or p.name
    ct = content_type or _detect_content_type(p)

    meta = {
        "mission_id": mission_id,
        "logical_name": ln,
        "object_type": object_type,          # e.g., "telemetry", "detections"
        "content_type": ct,
        "capture_time": int(time.time()),
        "sensor": sensor,
        "platform": platform,
        "classification": classification,
        "pipeline_run_id": pipeline_run_id,
        "tags": tags or {},
    }

    headers = {
        "X-MDM-Meta": json.dumps(meta),
        "Content-Type": ct,
    }
    if MDM_API_KEY:
        headers["X-API-Key"] = MDM_API_KEY

    with p.open("rb") as fh:
        resp = requests.post(MDM_URL, data=fh, headers=headers, timeout=timeout)

    try:
        resp.raise_for_status()
    except Exception:
        # include body in logs for quick diagnostics
        log.error("MDM ingest failed for %s (HTTP %s): %s", p.name, resp.status_code, resp.text.strip())
        raise

    try:
        out = resp.json()
    except Exception:
        out = {"ok": True, "raw_body": resp.text}

    log.info("MDM ingest ok: %s -> %s", p.name, out)
    return out

# Simple content type detection (default to octet-stream)
def _content_type_for(p: pathlib.Path) -> str:
    # default to octet-stream if unknown
    return mimetypes.guess_type(str(p))[0] or "application/octet-stream"

# Ingest a single file to MDM
def ingest_file(path: pathlib.Path, mission_id: str, mdm_url: str, api_key: Optional[str] = None) -> dict:
    logical_name = path.name
    # naive object type guess
    object_type = "telemetry" if logical_name.startswith("telemetry") else (
        "detections" if logical_name.startswith("detections") else "log"
    )
    content_type = _content_type_for(path)

    meta = {
        "mission_id": mission_id,
        "logical_name": logical_name,
        "object_type": object_type,
        "content_type": content_type,
        "capture_time": int(time.time()),
        "tags": {"segment": "demo", "source": "ground"},
    }
    headers = {
        "X-MDM-Meta": json.dumps(meta),
        "Content-Type": content_type,
    }
    if api_key:
        headers["X-API-Key"] = api_key

    with path.open("rb") as fh:
        r = requests.post(mdm_url, data=fh, headers=headers, timeout=60)
    r.raise_for_status()
    out = r.json()
    log.debug("ingested %s -> %s", path, out)
    return out

# Ingest all files in a mission directory to MDM
def ingest_mission_dir(mission_dir: pathlib.Path, mission_id: str, mdm_url: str, api_key: Optional[str] = None) -> Tuple[bool, str]:
    if not mission_dir.exists():
        return False, f"mission_dir not found: {mission_dir}"

    count, errors = 0, 0
    for p in sorted(mission_dir.glob("*")):
        if not p.is_file():
            continue
        try:
            ingest_file(p, mission_id, mdm_url, api_key)
            count += 1
        except Exception as e:
            errors += 1
            log.warning("ingest failed for %s: %s", p, e)

    msg = f"files_ingested={count} errors={errors}"
    return (errors == 0), msg