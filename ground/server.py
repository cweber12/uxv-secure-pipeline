# ground/server.py
# Ground station gRPC server with optional mTLS
from __future__ import annotations

import os
import sys
import ssl
import grpc
import asyncio
import pathlib
import hashlib
import json
import time
from typing import Tuple, Optional
from google.protobuf.json_format import MessageToDict


# Ensure repo root on sys.path so package imports work in both "python -m" and direct execution
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Make generated stubs importable (expects stubs in gen/python/)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "gen" / "python"))

import telemetry_pb2, telemetry_pb2_grpc
import detections_pb2, detections_pb2_grpc

from ground.recorder import JsonlRecorder

# ---------------------------- helpers ----------------------------

def _resolve_addr(host: str | None = None, port: int | None = None,
                  default_host: str = "127.0.0.1", default_port: int = 50051) -> Tuple[str, int]:
    """
    Resolve bind address from explicit args or environment.
    Supported envs (priority order):
      - BIND_ADDR or ADDR as 'host:port' or just 'host'
      - HOST and PORT separately
    """
    h = host or default_host
    p = port or default_port

    combo = os.getenv("BIND_ADDR") or os.getenv("ADDR")
    if combo:
        if ":" in combo:
            ch, cp = combo.rsplit(":", 1)
            if ch: h = ch
            try: p = int(cp)
            except ValueError: pass
        else:
            h = combo

    h = os.getenv("HOST", h)
    try:
        p = int(os.getenv("PORT", str(p)))
    except ValueError:
        pass

    return h, p


def _load_bytes(path: pathlib.Path, label: str) -> bytes:
    b = path.read_bytes()
    print(f"[tls] loaded {label} {path} bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()[:16]}")
    return b


def _server_credentials(cert_dir: pathlib.Path, require_client_auth: bool = True) -> grpc.ServerCredentials:
    """
    Build gRPC ServerCredentials for mTLS from PEM files in cert_dir:
      - ca.crt          (trust root to verify the client)
      - server.crt/.key (server chain/key)
    """
    ca_path      = cert_dir / "ca.crt"
    server_crt   = cert_dir / "server.crt"
    server_key   = cert_dir / "server.key"

    if not (ca_path.exists() and server_crt.exists() and server_key.exists()):
        raise FileNotFoundError(f"Missing certs in {cert_dir}. Need ca.crt, server.crt, server.key")

    ca_pem    = _load_bytes(ca_path, "ca.crt")
    cert_pem  = _load_bytes(server_crt, "server.crt")
    key_pem   = _load_bytes(server_key, "server.key")

    creds = grpc.ssl_server_credentials(
        private_key_certificate_chain_pairs=[(key_pem, cert_pem)],
        root_certificates=ca_pem if require_client_auth else None,
        require_client_auth=require_client_auth,
    )
    print(f"[tls] server credentials built (mTLS={'on' if require_client_auth else 'off'})")
    return creds


# ------------------------ gRPC services -------------------------

# TelemetryIngest service implementation
class TelemetryIngestService(telemetry_pb2_grpc.TelemetryIngestServicer):
    def __init__(self, recorder: JsonlRecorder):
        self.recorder = recorder

    async def StreamTelemetry(self, request_iterator, context):
        """
        Receives a stream of Telemetry messages, logs a summary line,
        and persists each one as a JSON object to missions/<id>/telemetry.jsonl.
        """
        count = 0
        async for msg in request_iterator:
            count += 1
            print(f"[telemetry] #{count} lat={msg.lat:.5f} lon={msg.lon:.5f} alt={msg.alt_m:.1f} ts={msg.ts_ns}")
            # Convert protobuf -> dict for JSON serialization
            obj = MessageToDict(msg, preserving_proto_field_name=True)
            self.recorder.write("telemetry", obj)
        print(f"[telemetry] stream closed, total={count}")
        return telemetry_pb2.TelemetryAck(ok=True)  

# DetectionIngest service implementation
class DetectionIngestService(detections_pb2_grpc.DetectionIngestServicer):
    def __init__(self, recorder: JsonlRecorder):
        self.recorder = recorder

    async def StreamDetections(self, request_iterator, context):
        """
        Receives a stream of Detection messages and writes them to missions/<id>/detections.jsonl.
        """
        count = 0
        async for d in request_iterator:
            count += 1
            bb = d.bbox
            print(f"[detection] #{count} {d.cls} conf={d.confidence:.2f} "
                  f"bbox=({bb.x:.1f},{bb.y:.1f},{bb.w:.1f},{bb.h:.1f}) ts={d.ts_ns}")
            obj = MessageToDict(d, preserving_proto_field_name=True)
            self.recorder.write("detections", obj)
        print(f"[detection] stream closed, total={count}")
        return detections_pb2.DetectionAck(ok=True)


# ----------------------- server bootstrap -----------------------

async def serve(host: str = "127.0.0.1", port: int = 50051):
    """
    Start gRPC server with optional mTLS (TLS=1 enables).
    Uses CERT_DIR (default `creds/`) for PEMs. Enforces client certs when TLS=1.
    """
    # Determine bind address
    tls_on   = os.getenv("TLS", "0") == "1"
    cert_dir = pathlib.Path(os.getenv("CERT_DIR", "creds")).resolve()
    host, port = _resolve_addr(host, port)

    mdm_url: Optional[str] = os.getenv("MDM_URL")          # e.g. http://127.0.0.1:8080/ingest
    mdm_api_key: str = os.getenv("MDM_API_KEY", "")

    mdm_url: Optional[str] = os.getenv("MDM_URL")          # e.g. http://127.0.0.1:8080/ingest
    mdm_api_key: str = os.getenv("MDM_API_KEY", "")

    recorder = JsonlRecorder(
        root=pathlib.Path("missions"),
        # Use the *correct* parameter name from your class: ingest_on_close
        ingest_on_close_flag=(os.getenv("MDM_INGEST_ON_CLOSE", "1") != "0"),
        mdm_url=mdm_url,
        mdm_api_key=mdm_api_key,
    )

    # Create gRPC server
    options = [
        ("grpc.max_receive_message_length", 20 * 1024 * 1024),
        ("grpc.keepalive_time_ms", 20000),
    ]
    server = grpc.aio.server(options=options)

    # Register services
    telemetry_pb2_grpc.add_TelemetryIngestServicer_to_server(TelemetryIngestService(recorder), server)
    detections_pb2_grpc.add_DetectionIngestServicer_to_server(DetectionIngestService(recorder), server)

    addr = f"{host}:{port}"
    if tls_on:
        # Build mTLS creds
        creds = _server_credentials(cert_dir, require_client_auth=True)
        bound = server.add_secure_port(addr, creds)
        print(f"[ground] TLS on @ {addr} (bound={bound})")
    else:
        bound = server.add_insecure_port(addr)
        print(f"[ground] PLAINTEXT @ {addr} (bound={bound})")

    if bound == 0:
        raise RuntimeError(f"Failed to bind gRPC server to {addr} (check permissions / address in use)")

    await server.start()
    print("[ground] server started")
    try:
    # start gRPC server etc...
        print("[ground] server started")
        await server.wait_for_termination()
    finally:
        try:
            recorder.close()  # triggers MDM POSTs per file if enabled
        except Exception as e:
            print(f"[recorder] close error: {e}")


if __name__ == "__main__":
    asyncio.run(serve())
