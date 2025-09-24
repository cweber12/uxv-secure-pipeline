# Edge Node

## Purpose

- Ingest sensor data (simulated or PX4 SITL) and camera frames.
- Run on-device CV inference (ONNX Runtime/TensorRT) to detect targets.
- Optionally embed MISB-style KLV in the video stream.
- Stream Telemetry & Detections via **gRPC** (mTLS) to Ground.
- Survive link loss using a local **ring buffer** and backpressure.

## Modules (planned)

- `sensor_sim/` or PX4 bridge
- `cv_infer/` (model loader, pre/post-processing)
- `video_pipeline/` (GStreamer/FFmpeg + KLV)
- `grpc_client/` (TelemetryIngest, DetectionIngest)
- `health/` (watchdog, metrics export)

## Run (later)

- `make edge-run` (TBD)
- Env vars for Ground URL, certs, model path, capture device.

## Notes

- Keep frame timestamps monotonic (`ts_ns`).
- Align inference output to frame index + `ts_ns`.
- Don’t block camera thread; use bounded queues.