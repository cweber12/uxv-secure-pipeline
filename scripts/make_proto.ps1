# make_proto.ps1
# PowerShell script to generate Python protobuf stubs

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Error "Activate your venv first: .\.venv\Scripts\Activate.ps1"
}

# Create output directory
mkdir -Force gen\python | Out-Null

# Install grpcio and grpcio-tools if not already installed
python -m pip install --upgrade pip grpcio grpcio-tools

# Generate Python gRPC stubs
python -m grpc_tools.protoc -I proto `
  --python_out=gen/python `
  --grpc_python_out=gen/python `
  proto/telemetry.proto proto/detections.proto

Write-Host "Protobuf Python stubs generated in gen\python"
