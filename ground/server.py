# ground/server.py
# gRPC server to receive telemetry and detection streams
import asyncio
import grpc
import sys, pathlib

# Make generated stubs importable (expects stubs in gen/python/)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "gen" / "python"))

import telemetry_pb2, telemetry_pb2_grpc
import detections_pb2, detections_pb2_grpc

from recorder import JsonlRecorder

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# -----------------------------------------------------------------------
# Implement the service classes defined in the .proto files
# -----------------------------------------------------------------------

# TelemetryIngest service implementation
class TelemetryIngestService(telemetry_pb2_grpc.TelemetryIngestServicer):
    def __init__(self, recorder: JsonlRecorder | None = None):
        self.rec = recorder
        """
        Args:
        recorder: optional JsonlRecorder to save incoming telemetry to disk
        """
    async def StreamTelemetry(self, request_iterator, context):
        """
        Stream handler for Telemetry messages.
        Args:
        request_iterator: an async iterator of Telemetry messages
        context: gRPC context (for metadata, cancellation, etc.)
        """
        count = 0 # count messages received
        # Process each incoming message
        async for msg in request_iterator:
            count += 1
            print(f"[telemetry] #{count} lat={msg.lat:.5f} lon={msg.lon:.5f} alt={msg.alt_m:.1f} ts={msg.ts_ns}")
             # record as dict
            if self.rec:
                self.rec.write("telemetry", {
                    "ts_ns": msg.ts_ns, "lat": msg.lat, "lon": msg.lon, "alt_m": msg.alt_m,
                    "yaw_deg": msg.yaw_deg, "pitch_deg": msg.pitch_deg, "roll_deg": msg.roll_deg,
                    "vn": msg.vn, "ve": msg.ve, "vd": msg.vd
                })
        print(f"[telemetry] stream closed, total={count}")
        return telemetry_pb2.TelemetryAck(ok=True)

# DetectionIngest service implementation
class DetectionIngestService(detections_pb2_grpc.DetectionIngestServicer):
    def __init__(self, recorder: JsonlRecorder | None = None):
        self.rec = recorder
    async def StreamDetections(self, request_iterator, context):
        count = 0
        async for d in request_iterator:
            count += 1
            bb = d.bbox
            print(f"[detection] #{count} {d.cls} conf={d.confidence:.2f} "
                  f"bbox=({bb.x:.1f},{bb.y:.1f},{bb.w:.1f},{bb.h:.1f}) ts={d.ts_ns}")
            # record as dict
            if self.rec:
                self.rec.write("detection", {
                    "ts_ns": d.ts_ns, "class": d.cls, "confidence": d.confidence,
                    "bbox": {"x": bb.x, "y": bb.y, "w": bb.w, "h": bb.h},
                    "lat": d.lat, "lon": d.lon
                })
        print(f"[detection] stream closed, total={count}")
        return detections_pb2.DetectionAck(ok=True)

# -----------------------------------------------------------------------
# Main server setup and loop
# -----------------------------------------------------------------------

# Start the gRPC server and listen for incoming connections
async def serve(host: str = "0.0.0.0", port: int = 50051):
    recorder = JsonlRecorder(root=pathlib.Path("missions"))
    server = grpc.aio.server(options=[
        # Increase max message size to 20 MiB
        ("grpc.max_receive_message_length", 20 * 1024 * 1024),
        # Enable keepalive pings every 20 seconds
        ("grpc.keepalive_time_ms", 20000),
    ])

    telemetry_pb2_grpc.add_TelemetryIngestServicer_to_server(TelemetryIngestService(recorder), server)
    detections_pb2_grpc.add_DetectionIngestServicer_to_server(DetectionIngestService(recorder), server)

    addr = f"{host}:{port}" # bind address
    server.add_insecure_port(addr)  # no TLS yet
    print(f"[ground] listening on {addr}")
    await server.start() # start the server
    try:
        await server.wait_for_termination()
    finally:
        recorder.close()

if __name__ == "__main__":
    asyncio.run(serve())
