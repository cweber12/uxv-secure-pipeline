# Ground Station

## Purpose

- Terminate mTLS gRPC streams (Telemetry/Detections).
- Fuse telemetry with detections by `ts_ns` and frame index.
- Extract MISB/KLV from video stream for verification (when present).
- Display live map + video; record to object storage; enable replay.
- Measure and report latency, loss, and pairing stats.

## Services (planned)

- `ingest_service/` (gRPC server: TelemetryIngest, DetectionIngest)
- `fusion/` (timestamp sync, buffering)
- `recorder/` (MP4 + JSON; resumable uploads)
- `ui/` (React/Vite + Leaflet/Maplibre)
- `metrics/` (Prometheus endpoint)

## Dev Run (later)

- `docker compose up ground`
- `make ground-run` (TBD)
- Configure S3-compatible store (minio for local).

## Testing

- Netem profiles for 1–10% loss, 20–200 ms RTT.
- Fuzz parsers; stress paired streams at 30–60 FPS.