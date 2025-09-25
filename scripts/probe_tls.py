# scripts/probe_tls.py
# Purpose: Probe a running gRPC server for readiness using a real TLS (mTLS) handshake.
# Exits 0 if the channel becomes READY within the timeout, non-zero otherwise.

from __future__ import annotations
import argparse
import os
import sys
import pathlib
from time import monotonic
import traceback

# Add generated protobuf stubs to path
gen_python = pathlib.Path(__file__).parent.parent / "gen" / "python"
if gen_python.exists():
    sys.path.insert(0, str(gen_python.resolve()))

try:
    import grpc
    print(f"[probe] gRPC version: {grpc.__version__}")
except ImportError as e:
    print(f"[probe] ERROR: Failed to import grpc: {e}")
    print(f"[probe] Python path: {sys.path}")
    sys.exit(2)


def _read_bytes(p: pathlib.Path) -> bytes:
    if not p.exists():
        print(f"[probe] ERROR: Certificate file missing: {p}")
        raise FileNotFoundError(f"missing file: {p}")
    size = p.stat().st_size
    print(f"[probe] Loading certificate: {p.name} ({size} bytes)")
    return p.read_bytes()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="gRPC TLS readiness probe (uses mTLS by default)."
    )
    # IMPORTANT: default to 'localhost' because the dev server cert CN is 'localhost'
    parser.add_argument(
        "--addr",
        default=os.getenv("ADDR", "localhost:50051"),
        help="host:port of the server (default: %(default)s)",
    )
    parser.add_argument(
        "--cert-dir",
        default=os.getenv("CERT_DIR", "creds"),
        help="directory containing ca.crt, client.crt, client.key (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("PROBE_TIMEOUT", "60")),
        help="seconds to wait for channel to become READY (default: %(default)s)",
    )
    parser.add_argument(
        "--override-host",
        default=os.getenv("TLS_OVERRIDE_HOST", "localhost"),
        help=(
            "override TLS server name for SNI/cert verification "
            "(useful if connecting via IP but cert CN is different). "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=os.getenv("TLS", "1") == "0",
        help="use insecure channel (no TLS). By default, mTLS is used.",
    )
    return parser.parse_args()


def make_channel(addr: str, cert_dir: pathlib.Path, override_host: str, insecure: bool):
    if insecure:
        print(f"[probe] Creating insecure channel to {addr}")
        return grpc.insecure_channel(addr), "insecure"

    print(f"[probe] Creating secure channel to {addr}")
    print(f"[probe] Certificate directory: {cert_dir.resolve()}")
    print(f"[probe] TLS override host: {override_host}")
    
    # Check certificate files exist
    cert_files = ["ca.crt", "client.key", "client.crt"]
    for cert_file in cert_files:
        cert_path = cert_dir / cert_file
        if not cert_path.exists():
            print(f"[probe] ERROR: Missing certificate file: {cert_path}")
            raise FileNotFoundError(f"Certificate file not found: {cert_path}")

    try:
        ca = _read_bytes(cert_dir / "ca.crt")
        client_key = _read_bytes(cert_dir / "client.key")
        client_crt = _read_bytes(cert_dir / "client.crt")
        print(f"[probe] All certificates loaded successfully")
    except Exception as e:
        print(f"[probe] ERROR: Failed to load certificates: {e}")
        raise

    try:
        creds = grpc.ssl_channel_credentials(
            root_certificates=ca,
            private_key=client_key,
            certificate_chain=client_crt,
        )
        print(f"[probe] SSL credentials created")
    except Exception as e:
        print(f"[probe] ERROR: Failed to create SSL credentials: {e}")
        raise

    # If connecting to 127.0.0.1 but cert CN is 'localhost', this override keeps verification happy.
    options = []
    if override_host:
        options.append(("grpc.ssl_target_name_override", override_host))
        print(f"[probe] Added SSL target name override: {override_host}")

    try:
        channel = grpc.secure_channel(addr, creds, options=options)
        print(f"[probe] Secure channel created")
        return channel, "mtls"
    except Exception as e:
        print(f"[probe] ERROR: Failed to create secure channel: {e}")
        raise


def main() -> int:
    try:
        args = parse_args()
        print(f"[probe] Starting probe with args: addr={args.addr}, cert_dir={args.cert_dir}, timeout={args.timeout}")
        print(f"[probe] Current working directory: {os.getcwd()}")
        print(f"[probe] Python executable: {sys.executable}")
        
        cert_dir = pathlib.Path(args.cert_dir)
        print(f"[probe] Certificate directory absolute path: {cert_dir.resolve()}")

        try:
            ch, mode = make_channel(args.addr, cert_dir, args.override_host, args.insecure)
        except Exception as e:
            print(f"[probe] ERROR: Failed to configure channel: {e}")
            traceback.print_exc()
            return 2

        print(f"[probe] Testing channel readiness with timeout {args.timeout}s...")
        deadline = monotonic() + max(1.0, args.timeout)
        
        try:
            timeout_remaining = max(1.0, deadline - monotonic())
            print(f"[probe] Waiting for channel ready (timeout: {timeout_remaining:.1f}s)...")
            grpc.channel_ready_future(ch).result(timeout=timeout_remaining)
            print(f"[probe] SUCCESS: gRPC channel READY ({mode}) to {args.addr}")
            return 0
        except grpc.FutureTimeoutError:
            print(f"[probe] ERROR: Timeout waiting for channel to become ready after {args.timeout}s")
            return 1
        except Exception as e:
            print(f"[probe] ERROR: Channel readiness check failed ({mode}) to {args.addr}: {type(e).__name__}: {e}")
            traceback.print_exc()
            
            # Helpful hints for common pitfalls
            if not args.insecure and ("hostname" in str(e).lower() or "handshake" in str(e).lower() or "certificate" in str(e).lower()):
                print(
                    "[probe] HINT: TLS/certificate issue detected. Common fixes:",
                )
                print(
                    "  - If server cert CN is 'localhost' but you're dialing an IP, try --addr localhost:50051",
                )
                print(
                    "  - Check that certificate files exist and are readable",
                )
                print(
                    "  - Verify server is actually running with TLS enabled",
                )
            return 1
        finally:
            try:
                ch.close()
                print(f"[probe] Channel closed")
            except:
                pass

    except Exception as e:
        print(f"[probe] FATAL ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
