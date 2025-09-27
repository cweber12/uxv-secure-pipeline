# scripts/probe_tls.py
# Simple script to probe gRPC server mTLS readiness
# Usage: python probe_tls.py --addr localhost:50051 --cert-dir creds --timeout 30 --sni localhost
import os, sys, time, pathlib, hashlib, grpc, argparse
from concurrent.futures import TimeoutError as FutureTimeoutError

# Ensure repo root on sys.path so package imports work in both "python -m" and direct execution
def _b(p: pathlib.Path) -> bytes:
    b = p.read_bytes()
    print(f"[probe]   - {p.name} exists={p.exists()} size={len(b)} sha256={hashlib.sha256(b).hexdigest()[:16]}")
    return b

# Allow CLI args to override defaults and env vars
def parse_args():
    ap = argparse.ArgumentParser(description="Probe gRPC mTLS readiness")
    ap.add_argument("--addr", default=os.getenv("ADDR", "127.0.0.1:50051"))
    ap.add_argument("--cert-dir", default=os.getenv("CERT_DIR", "creds"))
    ap.add_argument("--timeout", type=float, default=float(os.getenv("PROBE_TIMEOUT", "30.0")))
    ap.add_argument("--sni", default=os.getenv("SNI", "localhost"))
    return ap.parse_args()

def main():

    # Get args (with env var overrides)
    args = parse_args()

    cert_dir = pathlib.Path(args.cert_dir).resolve()
    addr     = args.addr
    timeout  = args.timeout
    sni      = args.sni

    # Log environment
    print(f"[probe] gRPC version: {grpc.__version__}")
    print(f"[probe] Starting probe with args: addr={addr}, cert_dir={cert_dir}, timeout={timeout}")
    print(f"[probe] Python: {sys.executable}")
    print(f"[probe] CWD: {pathlib.Path.cwd()}")
    print(f"[probe] GRPC_VERBOSITY={os.getenv('GRPC_VERBOSITY')} GRPC_TRACE={os.getenv('GRPC_TRACE')}")

    # Load certs
    ca = _b(cert_dir / "ca.crt")
    ck = _b(cert_dir / "client.key")
    cc = _b(cert_dir / "client.crt")

    # Create secure channel
    creds = grpc.ssl_channel_credentials(
        root_certificates=ca,
        private_key=ck,
        certificate_chain=cc,
    )
    
    if not creds:
        print("[probe] ERROR: failed to create credentials")
        sys.exit(3)

    # Options to match server settings and observe connectivity quickly
    opts = [
        ("grpc.ssl_target_name_override", sni),  # match server cert CN/SAN=localhost
        ("grpc.keepalive_time_ms", 10000),
        ("grpc.client_channel_backup_poll_interval_ms", 1000),
    ]

    print(f"[probe] Creating secure channel to {addr} (SNI={sni})")

    # Create channel and check ready
    ch = grpc.secure_channel(addr, creds, options=opts)
    if not ch:
        print("[probe] ERROR: failed to create channel")
        sys.exit(2)

    # Observe connectivity transitions quickly
    def watch(state):
        print(f"[probe] connectivity -> {state}")
    
    # Subscribe to connectivity changes
    ch.subscribe(watch, try_to_connect=True)

    print(f"[probe] Waiting for READY (timeout {timeout}s)…")

    # Wait for READY or timeout
    try:
        grpc.channel_ready_future(ch).result(timeout=timeout)
        print("[probe] READY: channel is secure and reachable.")
        sys.exit(0)
    except FutureTimeoutError:
        print("[probe] ERROR: Timeout waiting for READY")
        try:
            ch_state = ch._channel.check_connectivity_state(True)  # best effort
            print(f"[probe] final connectivity state: {ch_state}")
        except Exception:
            pass
        sys.exit(1)
    finally:
        ch.close()

if __name__ == "__main__":
    main()



