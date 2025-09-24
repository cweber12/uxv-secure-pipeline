# Protobuf Definitions (`proto/`)

This folder contains the **interface contracts** for the Secure UxV Telemetry & Video Pipeline.  
All communication between the **Edge (drone/robot)**, the **Ground station**, and the **Cloud API** goes through these contracts.

---

## Purpose

- Define the **shape of the data** (messages like `Telemetry` and `Detection`).
- Define the **services** (RPC methods) that let one component stream data to another.
- Ensure **type safety**: data is validated before it ever reaches your endpoint logic.
- Enable **multi-language support**: the same `.proto` file can generate client/server code in Go, Python, C++, JavaScript, and more.
- Provide **forward/backward compatibility**: new fields can be added later without breaking old clients.

---

## Files

### `telemetry.proto`

- Defines the `Telemetry` message: timestamp, GPS coordinates, altitude, orientation (yaw/pitch/roll), and velocities.
- Defines the `TelemetryIngest` service: a **streaming RPC** where the Edge continuously sends telemetry data to the Ground station.
- Includes an `Ack` message that the server returns when the stream finishes.

### `detections.proto`

- Defines the `Detection` message: bounding box, class label, confidence score, and optional GPS geo-tag.
- Defines the `DetectionIngest` service: a **streaming RPC** where the Edge sends detections (from computer vision inference) to the Ground station.
- Includes an `Ack` message to confirm successful receipt.

---

## Why the numbers (`= 1`, `= 2`, …)?

Each field in a message has a **field number**:

```proto
message Telemetry {
  int64 ts_ns = 1;
  double lat = 2;
  double lon = 3;
  double alt_m = 4;
}