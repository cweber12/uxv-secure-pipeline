# scripts\make_certs.ps1
# Generate a local dev CA, server cert, and client cert for mTLS (PEM files).
# Requires OpenSSL. If openssl isn't in PATH, we try Git for Windows' copy.

$ErrorActionPreference = "Stop"

# Locate openssl.exe
$openssl = (Get-Command openssl.exe -ErrorAction SilentlyContinue)
if (-not $openssl) {
  $gitOpenssl = "C:\Program Files\Git\usr\bin\openssl.exe"
  if (Test-Path $gitOpenssl) { $openssl = $gitOpenssl }
}
if (-not $openssl) {
  throw "OpenSSL not found. Install Git for Windows (includes openssl) or OpenSSL and ensure openssl.exe is in PATH."
}

# Create output dir
New-Item -ItemType Directory -Force -Path creds | Out-Null
Push-Location creds

# 1) Root CA
& $openssl genrsa -out ca.key 4096
& $openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 `
  -subj "/CN=uxv-dev-ca" -out ca.crt

# 2) Server cert (CN=localhost + SAN localhost/127.0.0.1)
& $openssl genrsa -out server.key 2048
& $openssl req -new -key server.key -subj "/CN=localhost" -out server.csr
@"
basicConstraints=CA:FALSE
subjectAltName=DNS:localhost,IP:127.0.0.1
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
"@ | Set-Content -Encoding ascii server.ext
& $openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial `
  -out server.crt -days 825 -sha256 -extfile server.ext

# 3) Client cert (CN=uxv-edge, clientAuth)
& $openssl genrsa -out client.key 2048
& $openssl req -new -key client.key -subj "/CN=uxv-edge" -out client.csr
@"
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
"@ | Set-Content -Encoding ascii client.ext
& $openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial `
  -out client.crt -days 825 -sha256 -extfile client.ext

# Clean up intermediates
Remove-Item -Force server.csr, client.csr, server.ext, client.ext, ca.srl -ErrorAction SilentlyContinue
Pop-Location

Write-Host "wrote creds\ (ca.crt, server.crt/key, client.crt/key)"
