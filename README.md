# Secure UxV Telemetry, Video & Targeting Pipeline

An end-to-end, **contracts-first** system for secure, low-latency ingest of UxV telemetry and video, with **on-edge target detection**, **MISB-style KLV tagging** (planned), **encrypted streaming to a ground station** (mTLS planned), and **cloud archiving/replay** (planned).

---

## What’s in this repo (current MVP)

- **Contracts**: Protobuf/gRPC interfaces in `proto/`.
- **Ground (Python)**: Minimal gRPC server that receives telemetry & detections, logs them, and **records to JSONL** for replay (`ground/`).
- **Edge (Python)**: Client simulator that streams synthetic telemetry & detections (`edge/`).
- **Edge Node (Node.js)**: Second-language client streaming the same messages using runtime proto loading (`edge-node/`).
- **CI**: GitHub Actions that compile `.proto` files to **Python stubs** and sanity-import them on every push/PR (`.github/workflows/ci.yml`).

> Video ingest, KLV extraction, cloud archive, and security hardening (mTLS) are on the roadmap below.

---

## Success Metrics (target)

- **E2E latency p95 ≤ 300 ms** @ 1080p30 (future video pipeline)
- **≥ 99.5%** frame↔telemetry pairing with **5% simulated packet loss** (future)
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

## Generate Protobuf Stubs (Python)

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

## Quickstart: Run the Demo

### Terminal A – Ground server:

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -u -m ground.server
# expected: "[ground] listening on 0.0.0.0:50051"
```

### Terminal B – Edge simulator:

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -u -m edge.client
# expected: "[edge] telemetry ack=True" and "[edge] detections ack=True"
```

## Ground output: logs each message, then:

```csharp
[telemetry] stream closed, total=10
[detection] stream closed, total=5
```

## Recorder output: JSONL files per mission:

```bash
missions/mission-YYYYMMDD-HHMMSS/
  telemetry.jsonl
  detections.jsonl
```

## Cross-Language Demo: Node Edge → Python Ground

### Install & run (with Ground already running):

```powershell
cd edge-node
npm install
npm start
# expected: "[node-edge] telemetry ack= true", "[node-edge] detections ack= true"
```

The Ground server logs should look the same as with the Python Edge.
The Node client loads ../proto/*.proto at runtime (no codegen) via @grpc/proto-loader.

## Security

Supports **mutual TLS (mTLS)** for all gRPC calls: encrypts traffic and **authenticates both client and server**.

### How to enable

- Set `TLS=1` to enable mTLS.
- Set `CERT_DIR` to the folder containing PEM files (default: `creds/`).

### Cert layout

```txt
creds/
    ca.crt       # Root CA
    server.crt   # Server cert (signed by CA)
    server.key   # Server key
    client.crt   # Client cert (signed by CA)
    client.key   # Client key
```

### Generate dev certs

**Windows (PowerShell):**

```powershell
.\scripts\make_certs.ps1
```

**macOS/Linux (Bash):**

```bash
bash scripts/make_certs.sh
```

### Run with mTLS

**Ground (server):**

```powershell
$env:TLS="1"; $env:CERT_DIR="creds"
python -u -m ground.server
```

**Edge (Python):**

```powershell
$env:TLS="1"; $env:CERT_DIR="creds"
python -u -m edge.client
```

**Edge (Node, optional):**

```powershell
$env:TLS="1"; $env:CERT_DIR="creds"
node .\edge-node\client.js
```

## CI (GitHub Actions)

- Installs protoc, sets up Python 3.11, and installs grpcio-tools.

- Compiles .proto → Python stubs into gen/python/ (ephemeral in CI).

- Sanity import: imports the generated modules to catch path/package issues early.

- Optional line-ending check (prevents CRLF noise).

This ensures the contracts are always valid and usable. We keep gen/ out of Git history and prove buildability on every push/PR.

## Development Workflow

- Edit .proto files in proto/.

- Regenerate stubs for your language(s). For Python, see commands above.
- For Node, no codegen needed; it loads .proto at runtime.

- Run Ground + Edge to validate end-to-end.

- Commit your changes (stubs in gen/ stay untracked).

Compatibility tip: Never reuse field numbers in .proto. If you remove a field, mark its number reserved.

## .gitignore (recommended)

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

## Troubleshooting

### ModuleNotFoundError: telemetry_pb2 / detections_pb2

- Regenerate stubs into gen/python/.

- Run from repo root so server.py / client.py can add gen/python to sys.path.

### No server prints

- Use unbuffered mode: python -u -m ground.server.

- If you switched to logging.info(...), ensure logging.basicConfig(level=logging.INFO, ...) is set.

### Node client can’t connect (ECONNREFUSED)

- Start Ground first; confirm same port (localhost:50051 by default).

### Windows line continuations

- Prefer the one-line PowerShell commands shown above.