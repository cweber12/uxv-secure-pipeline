# scripts/probe_tls.py  (sync version)
from __future__ import annotations
import argparse, os, sys, pathlib
from time import monotonic
import grpc

def _b(p: pathlib.Path) -> bytes:
    if not p.exists():
        raise FileNotFoundError(f"missing: {p}")
    return p.read_bytes()

def parse_args():
    ap = argparse.ArgumentParser("gRPC TLS readiness probe (mTLS)")
    ap.add_argument("--addr", default=os.getenv("ADDR","127.0.0.1:50051"))
    ap.add_argument("--cert-dir", default=os.getenv("CERT_DIR","creds"))
    ap.add_argument("--timeout", type=float, default=float(os.getenv("PROBE_TIMEOUT","60")))
    ap.add_argument("--override-host", default=os.getenv("TLS_OVERRIDE_HOST","localhost"))
    ap.add_argument("--insecure", action="store_true", default=os.getenv("TLS","1")=="0")
    return ap.parse_args()

def make_channel(addr: str, cert_dir: pathlib.Path, override: str, insecure: bool):
    if insecure:
        return grpc.insecure_channel(addr), "insecure"
    creds = grpc.ssl_channel_credentials(
        root_certificates=_b(cert_dir/"ca.crt"),
        private_key=_b(cert_dir/"client.key"),
        certificate_chain=_b(cert_dir/"client.crt"),
    )
    # Add BOTH override + default_authority to satisfy name checks and :authority on Windows
    opts = [
        ("grpc.ssl_target_name_override", override),
        ("grpc.default_authority", override),
    ]
    return grpc.secure_channel(addr, creds, options=opts), "mtls"

def main() -> int:
    args = parse_args()
    ch, mode = make_channel(args.addr, pathlib.Path(args.cert_dir), args.override_host, args.insecure)
    deadline = monotonic() + max(1.0, args.timeout)
    try:
        grpc.channel_ready_future(ch).result(timeout=max(1.0, deadline - monotonic()))
        print(f"[probe] READY ({mode}) -> {args.addr} as {args.override_host}")
        return 0
    except Exception as e:
        print(f"[probe] NOT READY ({mode}) -> {args.addr}: {e}")
        return 1
    finally:
        ch.close()

if __name__ == "__main__":
    sys.exit(main())
