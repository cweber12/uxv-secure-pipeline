# Secure `UxV` Telemetry, Video & Targeting Pipeline

An end-to-end, **contracts-first** system for secure, low-latency ingest of `UxV` telemetry and video, with **on-edge target detection**, **MISB-style KLV tagging** (planned), **encrypted streaming to a ground station** (mTLS planned), and **cloud archiving/replay** (planned).

---

## What’s in this repo (current MVP)

- **Contracts**: Protocol Buffer /gRPC interfaces in `proto/`.
- **Ground (Python)**: Minimal gRPC server that receives telemetry & detections, logs them, and **records to JSONL** for replay (`ground/`).
- **Edge (Python)**: Client simulator that streams synthetic telemetry & detections (`edge/`).
- **Edge Node (Node.js)**: Second-language client streaming the same messages using runtime proto loading (`edge-node/`).
- **CI**: GitHub Actions that compile `.proto` files to **Python stubs** and sanity-import them on every push/PR (`.github/workflows/ci.yml`).

> Video ingest, KLV extraction, cloud archive, and security hardening (mTLS) are on the roadmap below.

---

## Success Metrics (target)

- **E2E latency p95 ≤ 300 milliseconds** @ 1080p30 (future video pipeline)
- **≥ 99.5%** frame <-> telemetry pairing with **5% simulated packet loss** (future)
- **0 critical** findings in container/code scans (future CI gates)

---

## Repository Structure

```md
proto/ # Protobuf contracts (telemetry.proto, detections.proto)
ground/
server.py # gRPC server (receives streams, logs, records JSONL)
recorder.py # JSONL mission recorder
README.md
init.py
edge/
client.py # Python Edge simulator (streams telemetry + detections)
README.md
init.py
edge-node/
client.js # Node.js Edge client (grpc-js + proto-loader, no codegen)
package.json
README.md
docs/ # Architecture notes, ADRs (reserved for future additions)
.github/
workflows/
ci.yml # Proto build + sanity import (Python-based canary)
```

**Generated code** goes under `gen/` and is **not** committed. See `.gitignore` guidance below.

---

## Prerequisites

- **Python** 3.11+

- **Node.js** 18+ (for the Node Edge client)

## Setting Up Environment

```powershell
py -m venv .venv
..venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install grpcio grpcio-tools
```

---

## Generate Protocol Buffer Stubs (Python)

CI proves the protos compile, but for local runs you need stubs in `gen/python/`.

**PowerShell (Windows):**

```powershell
mkdir -Force gen\python
python -m grpc_tools.protoc -I proto `
--python_out=gen/python `
--grpc_python_out=gen/python `
proto\telemetry.proto proto\detections.proto
```

**Bash (macOS/Linux):**

```bash
mkdir -p gen/python
python -m grpc_tools.protoc -I proto \
  --python_out=gen/python \
  --grpc_python_out=gen/python \
  proto/telemetry.proto proto/detections.proto
```

## Quick Start: Run the Demo

### Terminal A – Ground server

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -u -m ground.server
# expected: "[ground] listening on 0.0.0.0:50051"
```

### Terminal B – Edge simulator

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -u -m edge.client
# expected: "[edge] telemetry ack=True" and "[edge] detections ack=True"
```

## Ground output: logs each message, then

```csharp
[telemetry] stream closed, total=10
[detection] stream closed, total=5
```

## Recorder output: JSONL files per mission

```bash
missions/mission-YYYYMMDD-HHMMSS/
  telemetry.jsonl
  detections.jsonl
```

## Cross-Language Demo: Node Edge → Python Ground

### Install & run (with Ground already running)

```powershell
cd edge-node
npm install
npm start
# expected: "[node-edge] telemetry ack= true", "[node-edge] detections ack= true"
```

The Ground server logs should look the same as with the Python Edge.
The Node client loads ../proto/*.proto at runtime (no `codegen`) via `@grpc/proto-loader`.

## Security

This project uses mutual TLS (mTLS) for secure communication between components.

### Certificate Generation

- Certificates are generated using the PowerShell script [`scripts/make_certs.ps1`](scripts/make_certs.ps1).
- The script creates a root CA, server, and client certificates with appropriate extensions and SANs for local development.
- All certificates and keys are stored in the `creds/` directory.

### Server-Side TLS

- The Ground server (`ground/server.py`) loads certificates from the `creds/` directory and enforces mTLS for all gRPC connections.
- The server verifies client certificates and only accepts connections from trusted clients.
- TLS parameters and certificate paths are configurable via environment variables (`TLS`, `CERT_DIR`, etc.).

### Client-Side TLS Probe

- The probe script [`scripts/probe_tls.py`](scripts/probe_tls.py) is used in CI and locally to verify that the Ground server is accepting secure connections.
- It loads the client certificate, key, and CA, and attempts to establish a secure gRPC channel to the server.
- The probe script reports detailed connectivity and certificate diagnostics for troubleshooting.

### Security Best Practices

- Never commit real production certificates or keys to the repository.
- The provided scripts and configuration are for local development and CI only.
- For production, generate and manage certificates using a secure process and store them in a protected location.
- Always verify certificate expiration and renewal policies.

---

## CI/CD

This project uses GitHub Actions for continuous integration and end-to-end testing. The main workflow is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Workflow Overview

- **Build Python gRPC stubs**: Generates Python code from protocol buffer definitions using `protoc` and `grpcio-tools`.
- **Create and activate Python virtual environment**: Installs dependencies in an isolated environment.
- **Generate test certificates**: Runs [`scripts/make_certs.ps1`](scripts/make_certs.ps1) to create mTLS certificates for secure local and CI testing.
- **Launch Ground server**: Starts the Ground server in the background with mTLS enabled, capturing logs for debugging.
- **Probe Ground server readiness**: Uses [`scripts/probe_tls.py`](scripts/probe_tls.py) to verify the server is accepting secure gRPC connections before running the Edge client.
- **Run Edge client**: Executes the Edge client and captures its output to `edge_py.log`.
- **Verify acknowledgments**: Checks the Edge client log for successful telemetry and detection acknowledgments.
- **Log collection and diagnostics**: On failure, outputs the last 200 lines of each log and the status of port 50051 for troubleshooting.
- **Artifact upload**: Uploads logs to GitHub Actions artifacts for review.

### Key Features

- All steps use PowerShell for cross-platform compatibility on Windows runners.
- Environment variables are set explicitly to ensure correct configuration for TLS and gRPC.
- The workflow automatically cleans up previous run artifacts and stops the Ground server after tests.
- The pipeline is designed to fail fast and provide detailed diagnostics if any step does not complete successfully.

---

## Development Workflow

- Edit .proto files in proto/.

- Regenerate stubs for your language(s). For Python, see commands above.
- For Node, no `codegen` needed; it loads .proto at runtime.

- Run Ground + Edge to validate end-to-end.

- Commit your changes (stubs in gen/ stay untracked).

Compatibility tip: Never reuse field numbers in .proto. If you remove a field, mark its number reserved.

## `.gitignore` (recommended)

Add/keep:

```gitignore
# Generated protobuf stubs and build artifacts
gen/
__pycache__/
*.pyc
.venv/
node_modules/
missions/
```

## Sending Data to the Mission Data Manager (MDM)

GitHub (MDM) : [GitHub](https://github.com/cweber12/mission-data-manager.git)

Ground can auto-ingest mission files when a mission closes. Set:
  Linux/macOS:  export MDM_URL="http://127.0.0.1:8080/ingest"  # optional: export MDM_API_KEY="your-key"
  Windows PS:   $env:MDM_URL = "http://127.0.0.1:8080/ingest"   # optional: $env:MDM_API_KEY = "your-key"

When the recorder closes, each file in missions/<mission_id>/ is POSTed to MDM. If MDM is down, files remain local; you can re-send them manually.

### HTTP Contract

- Endpoint:  POST /ingest
- Body:      raw file bytes
- Headers:
  - Content-Type: actual file type (e.g., `application/x-ndjson`, `application/octet-stream`)
  - X-MDM-Meta: JSON string (must include "mission_id"; others recommended: logical_name, object_type, content_type, capture_time, tags)
  - X-API-Key: (optional, if auth enabled)

## Troubleshooting

### ModuleNotFoundError: telemetry_pb2 / detections_pb2

- Regenerate stubs into gen/python/.

- Run from repo root so server.py / client.py can add gen/python to sys.path.

### No server prints

- Use unbuffered mode: python -u -m ground.server.

- If you switched to logging.info(...), ensure logging.basicConfig(level=logging.INFO, ...) is set.

### Node client can’t connect (ECONNREFUSED)

- Start Ground first; confirm same port (localhost:50051 by default).
