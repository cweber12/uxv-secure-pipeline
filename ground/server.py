# ground/server.py
import os
import sys
import ssl
import grpc
import asyncio
import pathlib
import hashlib
from typing import Tuple

# Make generated stubs importable (expects stubs in gen/python/)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "gen" / "python"))

import telemetry_pb2, telemetry_pb2_grpc
import detections_pb2, detections_pb2_grpc

from recorder import JsonlRecorder  # package import (ground/__init__.py present)

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

class TelemetryIngestService(telemetry_pb2_grpc.TelemetryIngestServicer):
    def __init__(self, recorder: JsonlRecorder | None = None):
        self.recorder = recorder

    async def StreamTelemetry(self, request_iterator, context):
        count = 0
        async for msg in request_iterator:
            count += 1
            print(f"[telemetry] #{count} lat={msg.lat:.5f} lon={msg.lon:.5f} alt={msg.alt_m:.1f} ts={msg.ts_ns}")
            if self.recorder:
                self.recorder.write("telemetry", msg)
        print(f"[telemetry] stream closed, total={count}")
        return telemetry_pb2.TelemetryAck(ok=True)


class DetectionIngestService(detections_pb2_grpc.DetectionIngestServicer):
    def __init__(self, recorder: JsonlRecorder | None = None):
        self.recorder = recorder

    async def StreamDetections(self, request_iterator, context):
        count = 0
        async for d in request_iterator:
            count += 1
            bb = d.bbox
            print(f"[detection] #{count} {d.cls} conf={d.confidence:.2f} "
                  f"bbox=({bb.x:.1f},{bb.y:.1f},{bb.w:.1f},{bb.h:.1f}) ts={d.ts_ns}")
            if self.recorder:
                self.recorder.write("detection", d)
        print(f"[detection] stream closed, total={count}")
        return detections_pb2.DetectionAck(ok=True)


# ----------------------- server bootstrap -----------------------

async def serve(host: str = "127.0.0.1", port: int = 50051):
    """
    Start gRPC server with optional mTLS (TLS=1 enables).
    Uses CERT_DIR (default `creds/`) for PEMs. Enforces client certs when TLS=1.
    """
    tls_on   = os.getenv("TLS", "0") == "1"
    cert_dir = pathlib.Path(os.getenv("CERT_DIR", "creds")).resolve()
    host, port = _resolve_addr(host, port)

    # Debug env variables that affect gRPC handshakes
    print(f"[env] GRPC_VERBOSITY={os.getenv('GRPC_VERBOSITY')} GRPC_TRACE={os.getenv('GRPC_TRACE')}")
    print(f"[env] TLS={os.getenv('TLS')} CERT_DIR={cert_dir} HOST={host} PORT={port}")

    recorder = JsonlRecorder(root=pathlib.Path("missions"))

    options = [
        ("grpc.max_receive_message_length", 20 * 1024 * 1024),
        ("grpc.keepalive_time_ms", 20000),
    ]
    server = grpc.aio.server(options=options)

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
        await server.wait_for_termination()
    finally:
        recorder.close()


if __name__ == "__main__":
    asyncio.run(serve())
