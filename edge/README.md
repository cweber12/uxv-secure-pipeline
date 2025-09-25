# Edge (Python)

A minimal **Python Edge simulator** that streams **telemetry** and **detections** to the Ground gRPC server using the shared `.proto` contracts. This demonstrates the contracts-first design and real-time client-streaming over gRPC.

---

## Purpose

- Generate synthetic flight **telemetry** and **detections** on the Edge side.
- Stream them to the **Ground** server via:
  - `TelemetryIngest.StreamTelemetry` (client-streaming)
  - `DetectionIngest.StreamDetections` (client-streaming)
- Receive a single **Ack** from the server when each stream closes.

---

## Folder Contents

edge/
client.py # Python Edge client: streams telemetry & detections
README.md # This file
init.py # (optional) add if you prefer running as a module: python -m edge.client

The client imports generated stubs from `gen/python/` (created from the `.proto` files).

---

## Prerequisites

- **Python 3.11+** (matches CI)
- A virtual environment and the gRPC runtime:
  
  ```powershell
  # from repo root (Windows PowerShell)
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install grpcio grpcio-tools
  ```

## Generated stubs for Python in gen/python/:

```powershell
mkdir -Force gen\python
python -m grpc_tools.protoc -I proto --python_out=gen/python --grpc_python_out=gen/python proto\telemetry.proto proto\detections.proto
```

CI already compiles the protos as a canary, but for local runs you need the files in gen/python/.

## How to Run

### Start the Ground server (separate terminal):

```powershell
.\.venv\Scripts\Activate.ps1
# If you added ground/__init__.py (recommended):
python -u -m ground.server
# Or without package mode:
# python -u .\ground\server.py
```

### Run the Edge client (repo root, new terminal):

```powershell
.\.venv\Scripts\Activate.ps1
# If you added edge/__init__.py:
python -u -m edge.client
# Or without package mode:
# python -u .\edge\client.py
```

## Expected output

### Client:

```csharp
[edge] telemetry ack=True
[edge] detections ack=True
```

### Ground: logs each received telemetry/detection and then:

```csharp
[telemetry] stream closed, total=10
[detection] stream closed, total=5
```

## What the Client Sends (Defaults)

- Telemetry: 10 messages at 5 Hz (every 200 ms) with gradually changing lat, lon, alt_m.

- Detections: 5 messages at 2 Hz with random confidence in [0.8, 1.0] and simple bbox increments.

- Timestamps: ts_ns based on time.monotonic_ns() (nanoseconds, monotonic clock).

- The server address defaults to localhost:50051 inside client.py. Edit the main() default if you need to target a different host/port.

## Troubleshooting

### ModuleNotFoundError: telemetry_pb2 / detections_pb2

- Ensure the stubs exist in gen/python/ (see “Generated stubs” above).

- Run from the repo root so the sys.path.insert(.../gen/python) line in client.py works.

### No output appears

- Use unbuffered mode: python -u ...

- Confirm the Ground server is running first and listening on the same port.

### Windows line continuation issues

- Prefer single-line commands in PowerShell (as shown) to avoid backtick/escaping problems.

### Firewall prompts

- Allow Python on private networks the first time you run the server/client.