# make_proto.ps1
# PowerShell script to generate Python protobuf stubs

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Error "Activate your venv first: .\.venv\Scripts\Activate.ps1"
}

mkdir -Force gen\python | Out-Null

python -m pip install --upgrade pip grpcio grpcio-tools

python -m grpc_tools.protoc -I proto `
  --python_out=gen/python `
  --grpc_python_out=gen/python `
  proto/telemetry.proto proto/detections.proto

Write-Host "Protobuf Python stubs generated in gen\python"
