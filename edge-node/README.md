# Edge Node (Node.js)

A minimal **Node.js Edge client** that streams **telemetry** and **detections** to the Ground gRPC server using the same `.proto` contracts as the Python implementation. The goal is to demonstrate **cross-language interoperability** (Node → Python or any language that implements the same services).

---

## Purpose

- Prove that a single set of **`Protobuf`/gRPC contracts** works across languages.
- Stream **client-side gRPC** to the Ground:
  - `TelemetryIngest.StreamTelemetry` (client-streaming)
  - `DetectionIngest.StreamDetections` (client-streaming)
- Receive and print the server’s final **Ack** for each stream.

---

## Contents

edge-node/
client.js # Node edge client (loads .proto at runtime; no `codegen` needed)
`package.json` # NPM metadata + dependencies `(@grpc/grpc-js, @grpc/proto-loader)`
README.md # This file

> The client loads `.proto` files directly from `../proto/` via `@grpc/proto-loader`.

---

## Prerequisites

- **Node.js** v18+ (LTS recommended)
- **Ground server** running locally (Python version from this repo):
  
  ```powershell
  # from repo root
  .\.venv\Scripts\Activate.ps1
  python -u -m ground.server
  ```

## Repo layout (relative paths assumed)

```txt
proto/
  telemetry.proto
  detections.proto
edge-node/
  client.js
  package.json
  README.md
```

## Quick Start

From the repo root:

```bash
cd edge-node
npm install
```

With the Ground server already listening:

```bash
# default: localhost:50051
npm start
```

### custom address via CLI `arg`

```bash
node client.js 192.168.1.50:50051
# or
ADDR=192.168.1.50:50051 npm start
```

## Expected output

```csharp
[node-edge] telemetry ack= true
[node-edge] detections ack= true
```

The Ground window logs each incoming message as it arrives.

## What the Client Sends (Defaults)

- Telemetry: 10 messages at 5 Hz (every 200 `ms`) with slightly changing `lat`, `lon`, and alt_m.

- Detections: 5 messages at 2 Hz, random confidence in [0.8, 1.0], simple bounding box increments.

- Timestamps: `ts_ns` in nanoseconds (sent as strings to avoid JS 64-bit integer precision issues).

You can adjust cadence/counts by editing the parameters in client.js (e.g., `n` and `hz`).

## How It Works

Runtime proto loading (no `codegen` step):

- Uses `@grpc/proto-loader` to load ../proto/telemetry.proto and ../proto/detections.proto.

Options: keepCase: true (preserves field names like `ts_ns`), longs: String (safe int64 handling).

## Client-streaming RPCs

- Opens a stream with StreamTelemetry / StreamDetections.

- Writes multiple messages at a fixed cadence.

- Calls end(); server replies with a single Ack ({ ok: true }).

## Troubleshooting

### ECONNREFUSED

Ground server not running or port blocked. Start the Python Ground server and/or check firewall prompts.

### Cannot find module '`@grpc/grpc-js`' or `@grpc/proto-loader`

Run `npm install` inside edge-node/.

### ENOENT (cannot find .proto)

Confirm repo structure and that client.js references ../proto/telemetry.proto and ../proto/detections.proto.

### No logs on Ground

Ensure you started Ground first, and that both processes target the same address (localhost:50051 by default)
