# ============================================
# scripts/make_certs.sh
# Generate local dev certificates for mTLS.
# Produces creds/{ca.crt,server.crt,server.key,client.crt,client.key}
# Usage: bash scripts/make_certs.sh
# ============================================

set -euo pipefail

OUT_DIR="creds"
mkdir -p "$OUT_DIR"
pushd "$OUT_DIR" >/dev/null

# 1) Root CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/CN=uxv-dev-ca" -out ca.crt

# 2) Server cert (CN=localhost + SANs)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=localhost" -out server.csr

cat > server.ext <<'EOF'
basicConstraints=CA:FALSE
subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile server.ext

# 3) Client cert (CN=uxv-edge, clientAuth)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -subj "/CN=uxv-edge" -out client.csr

cat > client.ext <<'EOF'
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 825 -sha256 -extfile client.ext

# Cleanup intermediates
rm -f server.csr client.csr server.ext client.ext ca.srl

popd >/dev/null
echo "wrote $OUT_DIR/ (ca.crt, server.crt/key, client.crt/key)"