# scripts/probe_tls.py
# Purpose: Probe a running gRPC server for readiness using a real TLS (mTLS) handshake.
# Exits 0 if the channel becomes READY within the timeout, non-zero otherwise.

from __future__ import annotations
import argparse
import os
import sys
import pathlib
from time import monotonic
import grpc


def _read_bytes(p: pathlib.Path) -> bytes:
    if not p.exists():
        raise FileNotFoundError(f"missing file: {p}")
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
        return grpc.insecure_channel(addr), "insecure"

    ca = _read_bytes(cert_dir / "ca.crt")
    client_key = _read_bytes(cert_dir / "client.key")
    client_crt = _read_bytes(cert_dir / "client.crt")

    creds = grpc.ssl_channel_credentials(
        root_certificates=ca,
        private_key=client_key,
        certificate_chain=client_crt,
    )

    # If connecting to 127.0.0.1 but cert CN is 'localhost', this override keeps verification happy.
    options = []
    if override_host:
        options.append(("grpc.ssl_target_name_override", override_host))

    return grpc.secure_channel(addr, creds, options=options), "mtls"


def main() -> int:
    args = parse_args()
    cert_dir = pathlib.Path(args.cert_dir)

    try:
        ch, mode = make_channel(args.addr, cert_dir, args.override_host, args.insecure)
    except Exception as e:
        print(f"[probe] failed to configure channel: {e}", file=sys.stderr)
        return 2

    deadline = monotonic() + max(1.0, args.timeout)
    try:
        grpc.channel_ready_future(ch).result(timeout=max(1.0, deadline - monotonic()))
        print(f"[probe] gRPC channel READY ({mode}) to {args.addr}")
        return 0
    except Exception as e:
        print(f"[probe] channel NOT ready ({mode}) to {args.addr}: {e}", file=sys.stderr)
        # Helpful hints for common pitfalls
        if not args.insecure and ("hostname" in str(e).lower() or "handshake" in str(e).lower()):
            print(
                "[probe] hint: if server cert CN is 'localhost' but you're dialing an IP, "
                "try --addr localhost:50051 or --override-host localhost",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
