# Architecture

## Overview
Edge (on-vehicle) → Ground (ingest, fusion, UI, record) → Cloud (archive, analytics).

```text
[ Edge ] --(mTLS gRPC: Telemetry/Detections)--> [ Ground ] --(S3/API)--> [ Cloud ]
   | CV infer (ONNX/TensorRT)                      | Recorder (MP4+JSON)     | Object store (S3)
   | KLV tagging (MISB-style)                      | KLV extraction           | Analytics (batch)
   | Ring buffer for link loss                     | UI (React/Leaflet)       | IAM/KMS