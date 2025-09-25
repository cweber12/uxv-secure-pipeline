// edge-node/client.js

// Simple gRPC client to send test telemetry and detection messages to the ground station server
// Run with: node edge-node/client.js
// Note: run python -u .\ground\server.py first to start the server
// Requires: npm install @grpc/grpc-js @grpc/proto-loader

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const PROTO_PATHS = [
  path.join(__dirname, '..', 'proto', 'telemetry.proto'),
  path.join(__dirname, '..', 'proto', 'detections.proto'),
];

// keepCase:true keeps field names like ts_ns
const pkgDef = protoLoader.loadSync(PROTO_PATHS, {
  keepCase: true, longs: String, enums: String, defaults: true, oneofs: true,
});

// Load the package definition
const proto = grpc.loadPackageDefinition(pkgDef).uxv.v1;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
/*
Send n telemetry messages at hz rate
Each message has:
    - timestamp (ns)
    - lat, lon, alt_m
    - yaw_deg, pitch_deg, roll_deg
    - vn, ve, vd (velocity NED)
*/
async function sendTelemetry(client, n = 10, hz = 5) {
  const periodMs = 1000 / hz; // time between messages in ms
  const t0 = BigInt(Date.now()) * 1000000n; // initial timestamp in ns
  const call = client.StreamTelemetry((err, ack) => {
    if (err) console.error('Telemetry error:', err);
    else console.log('[node-edge] telemetry ack=', ack?.ok);
  });

  for (let i = 0; i < n; i++) {
    call.write({
      ts_ns: (t0 + BigInt(i * periodMs) * 1000000n).toString(),
      lat: 32.70000 + 0.00010 * i,
      lon: -117.16000 - 0.00010 * i,
      alt_m: 120.0 + i * 0.5,
      yaw_deg: 10.0, pitch_deg: 0.5, roll_deg: 0.2,
      vn: 0.0, ve: 0.0, vd: 0.0,
    });
    await sleep(periodMs);
  }
  call.end();
}

// Send n detection messages at hz rate
// Each message has:
//    - timestamp (ns)
//    - class (string)
//    - confidence (float)
//    - bounding box (x, y, w, h)
//    - latitude (float)
//    - longitude (float)
async function sendDetections(client, n = 5, hz = 2) {
  const periodMs = 1000 / hz; 
  const t0 = BigInt(Date.now()) * 1000000n; 
  const call = client.StreamDetections((err, ack) => {
    if (err) console.error('Detections error:', err);
    else console.log('[node-edge] detections ack=', ack?.ok);
  });

  for (let i = 0; i < n; i++) {
    call.write({
      ts_ns: (t0 + BigInt(i * periodMs) * 1000000n).toString(),
      cls: 'target',
      confidence: 0.8 + Math.random() * 0.2,
      bbox: { x: 100 + i * 5, y: 150 + i * 3, w: 60, h: 40 },
      lat: 32.70, lon: -117.16,
    });
    await sleep(periodMs);
  }
  call.end();
}

// Main function to create clients and send messages
async function main(addr = 'localhost:50051') {
  const telClient = new proto.TelemetryIngest(addr, grpc.credentials.createInsecure());
  const detClient = new proto.DetectionIngest(addr, grpc.credentials.createInsecure());
  await Promise.all([sendTelemetry(telClient), sendDetections(detClient)]);
  console.log('[node-edge] done');
}

main().catch(err => (console.error(err), process.exit(1)));
