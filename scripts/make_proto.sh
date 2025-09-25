# ============================================
# scripts/make_proto.sh
# Generate Python protobuf/gRPC stubs from proto/*.proto
# Writes to gen/python/ (created if missing)
# Usage: bash scripts/make_proto.sh
# Env (optional):
#   PROTO_DIR=proto         # where .proto files live
#   OUT_PY=gen/python       # output dir for Python stubs
# ============================================

# If this file is sourced in the same shell (unlikely), guard re-execution:
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail

  PROTO_DIR="${PROTO_DIR:-proto}"
  OUT_PY="${OUT_PY:-gen/python}"

  # Verify grpc_tools is available
  if ! python3 -c "import grpc_tools.protoc" >/dev/null 2>&1; then
    echo "ERROR: Missing grpcio-tools. Install it first:"
    echo "  python3 -m pip install grpcio-tools"
    exit 1
  fi

  # Collect .proto files
  mapfile -t PROTOS < <(find "$PROTO_DIR" -maxdepth 1 -type f -name '*.proto' | sort)
  if [[ "${#PROTOS[@]}" -eq 0 ]]; then
    echo "ERROR: No .proto files found in '$PROTO_DIR'."
    exit 1
  fi

  mkdir -p "$OUT_PY"

  echo "Generating Python stubs → $OUT_PY"
  python3 -m grpc_tools.protoc -I "$PROTO_DIR" \
    --python_out="$OUT_PY" \
    --grpc_python_out="$OUT_PY" \
    "${PROTOS[@]}"

  echo "Python stubs generated in $OUT_PY"
fi