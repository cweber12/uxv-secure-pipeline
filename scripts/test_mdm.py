# scripts/test_mdm.py
# Simple tests for MDM HTTP ingestion service
import json, hashlib, os, sys, time, pathlib, requests

BASE = os.getenv("MDM_URL", "http://127.0.0.1:8080")

def assert_ok(r):
    try:
        r.raise_for_status()
    except Exception:
        print("Status:", r.status_code, "Body:", r.text)
        raise
    return r.json() if r.headers.get("content-type","").startswith("application/json") else r.text

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert_ok(r)

def test_ingest_meta():
    payload = {
        "mission_id": "mission-smoke-1",
        "logical_name": "telemetry.jsonl",
        "object_type": "telemetry",
        "content_type": "application/x-ndjson",
        "size_bytes": 456,
        "storage_tier": "LOCAL",
        "storage_path": "missions/mission-smoke-1/telemetry.jsonl",
        "tags": {"segment": "demo"}
    }
    r = requests.post(f"{BASE}/ingest/meta", json=payload, timeout=10)
    j = assert_ok(r)
    assert j["storage_tier"] == "LOCAL"

def test_ingest_bytes():
    p = pathlib.Path("artifact.bin"); p.write_bytes(b"hello mdm")
    meta = {
        "mission_id": "mission-smoke-2",
        "logical_name": "artifact.bin",
        "object_type": "log",
        "content_type": "application/octet-stream",
        "tags": {"segment":"demo"}
    }
    r = requests.post(
        f"{BASE}/ingest",
        headers={"X-MDM-Meta": json.dumps(meta), "Content-Type": "application/octet-stream"},
        data=p.read_bytes(),
        timeout=15
    )
    j = assert_ok(r)
    sha = hashlib.sha256(b"hello mdm").hexdigest()
    assert j["sha256"][:10] == sha[:10]

if __name__ == "__main__":
    test_health()
    test_ingest_meta()
    test_ingest_bytes()
    print("OK")
