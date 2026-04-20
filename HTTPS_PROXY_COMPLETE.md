# HIGH-GRAVITY HTTPS Proxy - Complete Implementation

## ✅ What Was Done

### 1. HTTPS Certificate System
- **Created**: `add_https_to_proxy.py` - Automated cert generation
- **Generates**: Self-signed certificate with 8 domain SANs
- **Installs**: Certificate to system trust store (`/usr/local/share/ca-certificates/`)
- **Updates**: `/etc/hosts` with all domain redirects

### 2. Dual HTTP/HTTPS Proxy
- **Updated**: `src/proxy.py` to run both HTTP (9999) and HTTPS (443)
- **Uses**: Multiprocessing to run both servers simultaneously
- **Supports**: All existing proxy features on both protocols

### 3. Integrated Startup
- **Enhanced**: `hg_start.sh` with automatic HTTPS setup
- **Auto-detects**: Certificates and enables HTTPS if available
- **Handles**: Sudo requirements for port 443
- **Preserves**: Python environment with `sudo -E`

### 4. Project Organization
- **Cleaned**: Root directory (11 files → cleaner structure)
- **Archived**: Old/redundant scripts to `archive/old_scripts/`
- **Organized**: Documentation to `docs/guides/`

## 📋 Files Created/Modified

### New Files
```
add_https_to_proxy.py          # HTTPS cert generator
certs/proxy.crt                # Self-signed certificate
certs/proxy.key                # Private key
docs/guides/WINDSURF_FIX_SUMMARY.md
archive/old_scripts/           # Archived files
```

### Modified Files
```
src/proxy.py                   # Dual HTTP/HTTPS support
hg_start.sh                    # Integrated HTTPS setup
/etc/hosts                     # Domain redirects
```

## 🔐 Certificate Details

**Domains Covered**:
- server.codeium.com
- inference.codeium.com
- server.self-serve.windsurf.com
- eu.windsurf.com
- windsurf.fedstart.com
- register.windsurf.com
- unleash.codeium.com
- shield.windsurf.com

**Installation**:
- System trust: `/usr/local/share/ca-certificates/high-gravity-proxy.crt`
- Certificate: `/mnt/DSMIL/HIGH-GRAVITY/certs/proxy.crt`
- Private key: `/mnt/DSMIL/HIGH-GRAVITY/certs/proxy.key`
- Validity: 365 days

## 🚀 Usage

### Quick Start
```bash
cd /mnt/DSMIL/HIGH-GRAVITY
bash hg_start.sh --clean
```

**What it does**:
1. Checks for HTTPS certificates
2. Generates them if missing (auto-installs to system)
3. Updates `/etc/hosts` with domain redirects
4. Starts proxy on HTTP (9999) and HTTPS (443)
5. Starts Khoj (optional)
6. Launches dashboard

### Manual HTTPS Setup
```bash
# Generate certificates only
python3 add_https_to_proxy.py

# Start proxy manually
sudo -E python3 src/proxy.py
```

### Verify HTTPS
```bash
# Check proxy is listening on both ports
lsof -i :9999 -i :443 | grep python3

# Test HTTPS connection
curl -v https://server.codeium.com:443

# Check certificate
openssl s_client -connect server.codeium.com:443 -CAfile certs/proxy.crt
```

## 🔍 How It Works

### Traffic Flow
```
Windsurf Language Server
    ↓
https://server.codeium.com
    ↓
DNS (/etc/hosts): 127.0.0.1
    ↓
HIGH-GRAVITY Proxy (port 443, HTTPS)
    ↓
[MITM Logging + Khoj Context]
    ↓
Real Codeium API (proxied)
```

### Why This Works
1. **Language server** has hardcoded URLs (can't patch binary)
2. **DNS redirect** via `/etc/hosts` → all domains resolve to localhost
3. **HTTPS proxy** on port 443 → accepts connections with valid cert
4. **System trust** → certificate installed, no SSL errors
5. **Dual protocol** → HTTP (9999) for extension, HTTPS (443) for language server

## 📊 Status Check

```bash
# Run status check
bash hg_status.sh
```

**Expected output**:
```
Proxy:     ✓ RUNNING (HTTP: 9999, HTTPS: 443)
Khoj:      ✓ RUNNING (Port: 42110)
Dashboard: ✓ RUNNING
Windsurf:  ✓ RUNNING
           ✓ MITM patch applied
```

## 🧪 Testing

### Test HTTPS Proxy
```bash
# Should connect successfully
curl -v https://server.codeium.com:443/

# Should show HIGH-GRAVITY proxy response
curl -v https://inference.codeium.com:443/hg/telemetry
```

### Test Windsurf Integration
```bash
# Restart Windsurf
pkill -f windsurf
/usr/share/windsurf-next/windsurf-next &

# Wait 30 seconds, then check connections
lsof -i -n -P | grep windsurf | grep 443

# Should show: 127.0.0.1:443 (NOT external IPs)
```

### Test MITM Logging
```bash
# Watch MITM log
tail -f logs/cascade_midway.log

# Use Cascade in Windsurf (Ctrl+L)
# Ask: "Hello, how are you?"

# Should see protocol events appear in log
```

## ⚙️ Configuration

### Disable HTTPS (HTTP only)
```bash
# Remove certificates
rm -rf certs/

# Start normally
bash hg_start.sh
# Will run HTTP-only on port 9999
```

### Regenerate Certificates
```bash
# Remove old certs
rm -rf certs/
sudo rm /usr/local/share/ca-certificates/high-gravity-proxy.crt
sudo update-ca-certificates

# Generate new
python3 add_https_to_proxy.py
```

### Add More Domains
Edit `add_https_to_proxy.py`:
```python
DOMAINS = [
    "server.codeium.com",
    # ... existing domains ...
    "your-new-domain.com",  # Add here
]
```

Then regenerate certificates.

## 🐛 Troubleshooting

### Proxy won't start on port 443
```bash
# Check if port is in use
sudo lsof -i :443

# Check sudo password
echo "1786" | sudo -S echo "Sudo works"

# Check Python environment
sudo -E python3 -c "import uvicorn; print('OK')"
```

### Certificate not trusted
```bash
# Reinstall certificate
sudo cp certs/proxy.crt /usr/local/share/ca-certificates/high-gravity-proxy.crt
sudo update-ca-certificates

# Verify installation
ls -la /etc/ssl/certs/ | grep high-gravity
```

### Windsurf still bypassing proxy
```bash
# Check /etc/hosts
cat /etc/hosts | grep codeium

# Check Windsurf connections
lsof -i -n -P | grep windsurf | grep ESTABLISHED

# Should see 127.0.0.1:443, NOT external IPs
```

### MITM log empty
```bash
# Check proxy is receiving requests
tail -f logs/proxy.log | grep "v1/chat"

# Check HG_OPT is loaded
grep "EXTENSION LOADED" logs/cascade_midway.log

# Restart Windsurf
pkill -f windsurf && /usr/share/windsurf-next/windsurf-next &
```

## 📚 Related Documentation

- `docs/guides/PATCHER_V2_GUIDE.md` - Extension patcher guide
- `docs/guides/WINDSURF_FIX_SUMMARY.md` - Root cause analysis
- `docs/guides/WINDSURF_MITM_FIX.md` - MITM implementation
- `README.md` - Main project documentation

## 🎯 Next Steps

1. **Test with Windsurf**: Use Cascade and verify MITM logging works
2. **Monitor logs**: Watch `logs/cascade_midway.log` for protocol events
3. **Verify Khoj**: Test context injection with Cascade queries
4. **Performance**: Monitor proxy performance with HTTPS overhead

## ✅ Success Criteria

- [x] HTTPS certificates generated and installed
- [x] Proxy runs on both HTTP (9999) and HTTPS (443)
- [x] `/etc/hosts` updated with domain redirects
- [x] Integrated into `hg_start.sh`
- [ ] Windsurf connects to localhost:443 (verify after restart)
- [ ] MITM log captures protocol events (verify with Cascade)
- [ ] No SSL errors in Windsurf (verify certificate trust)

## 🔐 Security Notes

- Self-signed certificate (not for production)
- Sudo password hardcoded in scripts (change for production)
- Certificate valid for 365 days (regenerate annually)
- All traffic intercepted (MITM by design)
- System trust store modified (can be reverted)

---

**Status**: ✅ Implementation Complete  
**Commit**: 6ca7421  
**Date**: 2026-04-20
