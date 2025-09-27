# scripts/make_certs.ps1
# PowerShell script to generate self-signed mTLS certificates for testing
param(
  [string]$OutDir = "creds",
  [int]$Days = 365
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OpenSSL = "openssl"

# 1) Root CA
& $OpenSSL genrsa -out "$OutDir\ca.key" 2048
& $OpenSSL req -x509 -new -nodes -sha256 -days $Days `
  -key "$OutDir\ca.key" -out "$OutDir\ca.crt" -subj "/CN=uxv-ca" `
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" `
  -addext "keyUsage=critical,keyCertSign,cRLSign"

# 2) Server key + CSR (CN=localhost) with SANs
& $OpenSSL genrsa -out "$OutDir\server.key" 2048
& $OpenSSL req -new -key "$OutDir\server.key" -out "$OutDir\server.csr" -subj "/CN=localhost"
$serverExt = @"
basicConstraints=CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
"@
Set-Content "$OutDir\server.ext" $serverExt -Encoding ascii
& $OpenSSL x509 -req -in "$OutDir\server.csr" -CA "$OutDir\ca.crt" -CAkey "$OutDir\ca.key" `
  -sha256 -days $Days -out "$OutDir\server.crt" -extfile "$OutDir\server.ext"

# 3) Client key + CSR (CN=uxv-edge) with clientAuth EKU
& $OpenSSL genrsa -out "$OutDir\client.key" 2048
& $OpenSSL req -new -key "$OutDir\client.key" -out "$OutDir\client.csr" -subj "/CN=uxv-edge"
$clientExt = @"
basicConstraints=CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = uxv-edge
"@
Set-Content "$OutDir\client.ext" $clientExt -Encoding ascii
& $OpenSSL x509 -req -in "$OutDir\client.csr" -CA "$OutDir\ca.crt" -CAkey "$OutDir\ca.key" `
  -sha256 -days $Days -out "$OutDir\client.crt" -extfile "$OutDir\client.ext"

Write-Host "wrote $OutDir\ (ca.crt, server.crt/key, client.crt/key)"

