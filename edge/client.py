# edge/client.py
import asyncio
import os
import time
import pathlib
import grpc

# Allow running from repo root
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "gen" / "python"))

import telemetry_pb2, telemetry_pb2_grpc
import detections_pb2, detections_pb2_grpc


def _read_bytes(p: pathlib.Path) -> bytes:
    return p.read_bytes()


def make_channel(addr: str) -> grpc.aio.Channel:
    """
    Create a gRPC channel.
    TLS=1 enables mTLS using CERT_DIR (ca.crt, client.crt, client.key).
    TLS_OVERRIDE_HOST can be set to e.g. 'localhost' when dialing an IP like 127.0.0.1.
    """
    use_tls = os.getenv("TLS", "0") == "1"
    if not use_tls:
        return grpc.aio.insecure_channel(addr)

    cert_dir = pathlib.Path(os.getenv("CERT_DIR", "creds"))
    ca = _read_bytes(cert_dir / "ca.crt")
    client_key = _read_bytes(cert_dir / "client.key")
    client_crt = _read_bytes(cert_dir / "client.crt")

    creds = grpc.ssl_channel_credentials(
        root_certificates=ca,
        private_key=client_key,
        certificate_chain=client_crt,
    )

    options = []
    override = os.getenv("TLS_OVERRIDE_HOST", "")
    if override:
        # Needed when dialing 127.0.0.1 but server cert CN is 'localhost'
        options.append(("grpc.ssl_target_name_override", override))

    return grpc.aio.secure_channel(addr, creds, options=options)


async def send_telemetry(stub: telemetry_pb2_grpc.TelemetryIngestStub, n=10, hz=5):
    period = 1.0 / hz
    t0 = time.monotonic_ns()
    async def gen():
        for i in range(n):
            yield telemetry_pb2.Telemetry(
                ts_ns=t0 + i * int(period * 1e9),
                lat=32.70000 + 0.00010 * i,
                lon=-117.16000 - 0.00010 * i,
                alt_m=120.0 + i * 0.5,
                yaw_deg=10.0, pitch_deg=0.5, roll_deg=0.2,
                vn=0.0, ve=0.0, vd=0.0,
            )
            await asyncio.sleep(period)
    ack = await stub.StreamTelemetry(gen())
    print(f"[edge] telemetry ack={ack.ok}")


async def send_detections(stub: detections_pb2_grpc.DetectionIngestStub, n=5, hz=2):
    period = 1.0 / hz
    t0 = time.monotonic_ns()
    async def gen():
        for i in range(n):
            yield detections_pb2.Detection(
                ts_ns=t0 + i * int(period * 1e9),
                cls="target", confidence=min(1.0, 0.8 + 0.05 * i),
                bbox=detections_pb2.BBox(x=100 + 5 * i, y=150 + 3 * i, w=60, h=40),
                lat=32.70, lon=-117.16,
            )
            await asyncio.sleep(period)
    ack = await stub.StreamDetections(gen())
    print(f"[edge] detections ack={ack.ok}")


async def main():
    addr = os.getenv("ADDR", "127.0.0.1:50051")
    ch = make_channel(addr)
    tel = telemetry_pb2_grpc.TelemetryIngestStub(ch)
    det = detections_pb2_grpc.DetectionIngestStub(ch)
    await asyncio.gather(send_telemetry(tel), send_detections(det))
    await ch.close()


if __name__ == "__main__":
    asyncio.run(main())
