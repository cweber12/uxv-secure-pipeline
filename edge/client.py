# edge/client.py
# gRPC client to send telemetry and detection streams
import asyncio, time
import grpc
import sys, pathlib
from random import random

# Make generated stubs importable (expects stubs in gen/python/)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "gen" / "python"))

import telemetry_pb2, telemetry_pb2_grpc
import detections_pb2, detections_pb2_grpc


async def send_telemetry(stub: telemetry_pb2_grpc.TelemetryIngestStub, n=10, hz=5):
    """
    Sends n telemetry messages at the specified rate, then waits for and prints the server's ack.
    Args:
    stub: a gRPC client object for the TelemetryIngest service
    n: how many telemetry messages to send
    hz: how often per second to send them
    """
    period = 1.0 / hz # seconds between messages
    t0 = time.monotonic_ns() # starting timestamp in nanoseconds
    async def gen():
        for i in range(n):
            yield telemetry_pb2.Telemetry(
                ts_ns=t0 + i * int(period * 1e9), # simulate regular intervals
                lat=32.70000 + 0.00010 * i, # simulate northward movement
                lon=-117.16000 - 0.00010 * i, # simulate westward movement
                alt_m=120.0 + i * 0.5, # simulate gradual ascent
                yaw_deg=10.0, pitch_deg=0.5, roll_deg=0.2, # fixed orientation
                vn=0.0, ve=0.0, vd=0.0, # stationary
            )
            await asyncio.sleep(period) # spacing messages out to simulate real-time telemetry
    ack = await stub.StreamTelemetry(gen()) # send the stream and wait for the ack
    print(f"[edge] telemetry ack={ack.ok}") # print the ack result


async def send_detections(stub: detections_pb2_grpc.DetectionIngestStub, n=5, hz=2):
    """
    Sends n detection messages at the specified rate, then waits for and prints the server's ack.
    Args:
    stub: a gRPC client object for the DetectionIngest service
    n: how many detection messages to send
    hz: how often per second to send them
    """
    period = 1.0 / hz 
    t0 = time.monotonic_ns() 
    async def gen():
        for i in range(n):
            yield detections_pb2.Detection(
                ts_ns=t0 + i * int(period * 1e9), 
                cls="target", # class label
                confidence=0.8 + 0.2 * random(), # simulate varying confidence
                bbox=detections_pb2.BBox(x=100+i*5, y=150+i*3, w=60, h=40), # simulate moving bbox
                lat=32.70, lon=-117.16, # fixed location
            )
            await asyncio.sleep(period)
    ack = await stub.StreamDetections(gen())
    print(f"[edge] detections ack={ack.ok}")


async def main(server_addr="localhost:50051"):
    """
    Main entry point for the gRPC client.
    """
    # Create a channel and stubs, then concurrently send telemetry and detections
    async with grpc.aio.insecure_channel(server_addr) as channel:
        tel_stub = telemetry_pb2_grpc.TelemetryIngestStub(channel)
        det_stub = detections_pb2_grpc.DetectionIngestStub(channel)
        # Run both sending tasks concurrently
        await asyncio.gather(
            send_telemetry(tel_stub),
            send_detections(det_stub),
        )

if __name__ == "__main__":
    asyncio.run(main())
