# Secure UxV Telemetry, Video & Targeting Pipeline

An end-to-end, contracts-first system for **secure low-latency ingest** of UxV telemetry and video, with **on-edge target detection**, **MISB-style KLV tagging**, **encrypted streaming to a ground station**, and **cloud archiving/replay**.

## MVP Scope

- Telemetry & detections streamed via **gRPC** (contracts in `proto/`).
- Edge: CV inference + optional KLV tagging.
- Ground: live map/video, recording to object storage, simple replay.
- Cloud: storage layout + stub analytics (counts/timelines).

## Success Metrics

- **E2E latency p95 ≤ 300 ms** @ 1080p30
- **≥ 99.5%** frame↔telemetry pairing with **5% simulated packet loss**
- **0 critical** findings in container/code scans

## Repo Structure

proto/ # Protobuf contracts (telemetry, detections)
edge/ # Edge node (sensor sim, CV, KLV, transmit)
ground/ # Ground ingest, fusion, KLV extract, UI, recorder
cloud/ # Ingest API, object storage, analytics, IaC
tools/ # Protoc toolchain, simulators, linters/scanners
docs/ # Architecture, ADRs, standards mapping
.github/ # CI workflows

## Quickstart: Protos

> You can generate stubs in multiple languages. Below shows Go and Python examples.

### Go

```bash
sudo apt-get install -y protobuf-compiler golang
make proto-go