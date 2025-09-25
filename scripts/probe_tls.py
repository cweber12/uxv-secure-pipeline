# scripts/probe_tls.py
import os, sys, time, pathlib, hashlib, grpc
from concurrent.futures import TimeoutError as FutureTimeoutError

def _b(p: pathlib.Path) -> bytes:
    b = p.read_bytes()
    print(f"[probe]   - {p.name} exists={p.exists()} size={len(b)} sha256={hashlib.sha256(b).hexdigest()[:16]}")
    return b

def main():
    addr     = os.getenv("ADDR", "127.0.0.1:50051")
    cert_dir = pathlib.Path(os.getenv("CERT_DIR", "creds")).resolve()
    timeout  = float(os.getenv("PROBE_TIMEOUT", "30.0"))
    sni      = os.getenv("SNI", "localhost")

    print(f"[probe] gRPC version: {grpc.__version__}")
    print(f"[probe] Starting probe with args: addr={addr}, cert_dir={cert_dir}, timeout={timeout}")
    print(f"[probe] Python: {sys.executable}")
    print(f"[probe] CWD: {pathlib.Path.cwd()}")

    ca = _b(cert_dir / "ca.crt")
    ck = _b(cert_dir / "client.key")
    cc = _b(cert_dir / "client.crt")

    creds = grpc.ssl_channel_credentials(root_certificates=ca,
                                         private_key=ck,
                                         certificate_chain=cc)

    opts = [
        ("grpc.ssl_target_name_override", sni),  # match server cert CN/SAN=localhost
        ("grpc.keepalive_time_ms", 10000),
    ]
    print(f"[probe] Creating secure channel to {addr} (SNI={sni})")
    ch = grpc.secure_channel(addr, creds, options=opts)

    # Observe connectivity transitions quickly
    def watch(state):
        print(f"[probe] connectivity -> {state}")
    ch.subscribe(watch, try_to_connect=True)

    print(f"[probe] Waiting for READY (timeout {timeout}s)…")
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



