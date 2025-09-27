# Ground (Python)

The **Ground** service is a minimal gRPC server that receives **telemetry** and **detections** from an Edge client using the shared `.proto` contracts. It logs incoming messages and (optionally) **records them to JSONL files** for replay/analysis.

---

## Purpose

- Implement the server-side of the contracts-first design.
- Receive client-streaming RPCs:
  - `TelemetryIngest.StreamTelemetry` (telemetry stream → single Ack)
  - `DetectionIngest.StreamDetections` (detections stream → single Ack)
- Provide a simple **mission recorder** that persists streams to disk.

---

## Folder Contents

```txt
ground/
server.py # gRPC server: handles telemetry & detections streams
recorder.py # JSONL mission recorder (writes telemetry/detections to disk)
README.md # This file
init.py # Marks 'ground' as a package (so you can run: python -m ground.server)
```

The server imports generated stubs from `gen/python/` (built from the `.proto` files).

---

## Prerequisites

- **Python** 3.11+ (matches CI)
- A virtual environment and the Python gRPC runtime:

  ```powershell
  # from repo root (Windows PowerShell)
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install grpcio grpcio-tools
  ```

## Generated stubs (Python) in gen/python/

```powershell
mkdir -Force gen\python
python -m grpc_tools.protoc -I proto `
  --python_out=gen/python `
  --grpc_python_out=gen/python `
  proto\telemetry.proto proto\detections.proto
```

CI also compiles the protos as a canary, but for local runs the files must exist under gen/python/.

## How to Run

### Recommended (package mode)

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -u -m ground.server
```

### Alternative (script mode)

```powershell
# from repo root
python -u .\ground\server.py
```

## You should see

```csharp
[ground] listening on 0.0.0.0:50051
```

When an Edge client connects and streams data, the server logs each message and returns a final Ack when the stream closes.

Pair with the Python Edge (edge/client.py) or Node Edge (edge-node/client.js) to see data flow end-to-end.

## Mission Recorder (JSONL)

The recorder writes each message as one JSON object per line to a mission folder:

```arduino
missions/
  mission-YYYYMMDD-HHMMSS/
    telemetry.jsonl   # stream of Telemetry messages
    detections.jsonl  # stream of Detection messages
```

Each line is append-only and flushes on write (handy for demos and tailing). Example `telemetry.jsonl` line:

```json
{"ts_ns":1256911702889300,"lat":32.7000,"lon":-117.1600,"alt_m":120.0,"yaw_deg":10.0,"pitch_deg":0.5,"roll_deg":0.2,"vn":0.0,"ve":0.0,"vd":0.0}
```

And a `detections.jsonl` line:

```json
{"ts_ns":1256911703001200,"cls":"target","confidence":0.91,"bbox":{"x":100,"y":150,"w":60,"h":40},"lat":32.70,"lon":-117.16}
```

Folder creation and file rotation are handled automatically per mission. Close/cleanup happens on server shutdown.

## Configuration Notes

- Address/Port: Defaults to 0.0.0.0:50051. Edit the defaults in serve() if needed.

- Message sizes / keepalive: server.py includes options for larger messages and periodic keepalive pings.

- Security: The demo runs insecure (no TLS) to keep setup simple. Replace with mTLS for production-grade security.

- Stub imports: server.py prepends gen/python to sys.path. Alternatively, set PYTHONPATH=gen/python before running.

## Expected Flow

1. Start Ground (this server) → prints listening address.

2. Start an Edge client (Python or Node) → streams telemetry & detections.

3. Ground logs each message and writes to `missions/<id>/*.jsonl` (if recorder enabled).

4. Server returns an Ack when each stream ends; client prints ack=True.

## Troubleshooting

### ModuleNotFoundError: telemetry_pb2 / detections_pb2

- Ensure stubs exist under gen/python/.

- Run from the repo root so the path adjustment in server.py works.

### ModuleNotFoundError: No module named 'ground'

- Ensure `ground/__init__.py` exists and run with python -m ground.server from the repo root,
- or switch from ground.recorder import ... to a relative import (from .recorder import ...).

### No output appears

- Use unbuffered mode: python -u -m ground.server.

- Confirm the Edge client is running and targeting the same port.

### Port already in use

- Choose a different port in serve() (e.g., 50052) and update the client.

### Windows firewall prompts

- Allow Python on private networks on first run
