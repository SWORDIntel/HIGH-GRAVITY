#!/bin/bash
# Master Certificate Generator for HIGH-GRAVITY Expert Shield

CERT_DIR="certs"
mkdir -p "$CERT_DIR"

echo "[*] Generating Master CA..."
# 1. Generate Root CA
openssl genrsa -out "$CERT_DIR/proxy.ca.key" 4096 2>/dev/null
openssl req -x509 -new -nodes -key "$CERT_DIR/proxy.ca.key" -sha256 -days 3650 \
    -subj "/C=UK/ST=London/L=London/O=SWORDIntel/OU=ExpertShield/CN=HIGH-GRAVITY Master CA" \
    -out "$CERT_DIR/proxy.ca.crt" 2>/dev/null

echo "[*] Generating Server Certificate with SANs..."
# 2. Generate Server CSR
openssl genrsa -out "$CERT_DIR/proxy.key" 2048 2>/dev/null
openssl req -new -key "$CERT_DIR/proxy.key" \
    -subj "/C=UK/ST=London/L=London/O=SWORDIntel/OU=ExpertShield/CN=proxy.windsurf.com" \
    -out "$CERT_DIR/proxy.csr" 2>/dev/null

# 3. Create SAN Extension
cat > "$CERT_DIR/proxy.ext" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = proxy.windsurf.com
DNS.2 = inferapi.windsurf.com
DNS.3 = server.codeium.com
DNS.4 = inference.codeium.com
DNS.5 = server.self-serve.windsurf.com
DNS.6 = unleash.codeium.com
DNS.7 = southcentral-lb.codeium.com
DNS.8 = api.codeium.com
DNS.9 = localhost
IP.1 = 127.0.0.1
EOF

# 4. Sign Certificate
openssl x509 -req -in "$CERT_DIR/proxy.csr" -CA "$CERT_DIR/proxy.ca.crt" -CAkey "$CERT_DIR/proxy.ca.key" \
    -CAcreateserial -out "$CERT_DIR/proxy.crt" -days 3650 -sha256 -extfile "$CERT_DIR/proxy.ext" 2>/dev/null

# 5. Trust the CA (System wide)
echo "[*] Installing CA to system trust store..."
sudo cp "$CERT_DIR/proxy.ca.crt" /usr/local/share/ca-certificates/high-gravity-ca.crt
sudo update-ca-certificates

echo "[+] Master Certificate Generated and Trusted."
