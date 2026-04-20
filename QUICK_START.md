# HIGH-GRAVITY Quick Start Guide

## 🚀 Complete Setup (One-Time)

### Step 1: Close Windsurf
```bash
pkill -f windsurf
```

### Step 2: Apply All Patches
```bash
cd /mnt/DSMIL/HIGH-GRAVITY
bash apply_all_patches.sh
```

**What it does:**
- Patches extension.js (8 URL replacements)
- Patches language server binary (2 URL replacements)
- Adds /etc/hosts DNS redirects (3 domains)
- Creates backup at `language_server_linux_x64.original`

**Triple-layer approach catches all URLs:**
- Extension patches: Some hardcoded URLs
- Binary patches: Binary-embedded URLs  
- DNS redirects: Runtime-constructed URLs

### Step 3: Start HIGH-GRAVITY
```bash
bash hg_start.sh --clean
```

**What it does:**
- Starts HTTP proxy on port 9999
- Starts Khoj semantic search on port 42110
- Launches dashboard

### Step 4: Start Windsurf
```bash
/usr/share/windsurf-next/windsurf-next &
```

### Step 5: Verify Integration
```bash
# Wait 30 seconds, then check connections
lsof -i -n -P | grep windsurf | grep 9999

# Should show connections to 127.0.0.1:9999
```

### Step 6: Test Cascade
1. Press `Ctrl+L` in Windsurf
2. Ask: "Hello, how are you?"
3. Watch MITM log:
```bash
tail -f logs/cascade_midway.log
```

**Should see protocol events appear!**

---

## 📊 Daily Usage

### Start Everything
```bash
bash hg_start.sh
```

### Stop Everything
```bash
bash hg_stop.sh
```

### Check Status
```bash
bash hg_status.sh
```

### View Logs
```bash
# Proxy traffic
tail -f logs/proxy.log

# MITM events
tail -f logs/cascade_midway.log

# Khoj search
tail -f logs/khoj.log
```

---

## 🔧 Troubleshooting

### Windsurf Not Using Proxy

**Check connections:**
```bash
lsof -i -n -P | grep windsurf | grep ESTABLISHED
```

**Should show:** `127.0.0.1:9999`  
**Should NOT show:** External IPs like `35.223.238.178`

**If showing external IPs:**
1. Close Windsurf: `pkill -f windsurf`
2. Re-patch binary: `bash patch_windsurf_binary.sh`
3. Restart: `/usr/share/windsurf-next/windsurf-next &`

### MITM Log Empty

**Check proxy is receiving requests:**
```bash
tail -f logs/proxy.log | grep "v1/chat"
```

**If no requests:**
- Verify binary is patched: `python3 src/patch_language_server_binary.py --verify`
- Check proxy is running: `lsof -i :9999`
- Restart Windsurf

### Restore Original Binary

**If something breaks:**
```bash
pkill -f windsurf
python3 src/patch_language_server_binary.py --restore
/usr/share/windsurf-next/windsurf-next &
```

---

## 🎯 Verification Checklist

After setup, verify:

- [ ] Proxy running on port 9999
- [ ] Khoj running on port 42110
- [ ] Windsurf connects to `127.0.0.1:9999`
- [ ] MITM log populates when using Cascade
- [ ] No external IP connections from Windsurf

**Run full verification:**
```bash
bash hg_status.sh
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `patch_windsurf_binary.sh` | Patch language server binary |
| `hg_start.sh` | Start all services |
| `hg_stop.sh` | Stop all services |
| `hg_status.sh` | Check service status |
| `logs/cascade_midway.log` | MITM protocol events |
| `logs/proxy.log` | Proxy traffic log |

---

## 🔄 After Windsurf Updates

When Windsurf updates, the binary is replaced:

```bash
# 1. Close Windsurf
pkill -f windsurf

# 2. Re-patch binary
bash patch_windsurf_binary.sh

# 3. Restart
/usr/share/windsurf-next/windsurf-next &
```

---

## 🆘 Getting Help

**Check logs:**
```bash
# Proxy errors
tail -50 logs/proxy.log

# MITM events
tail -50 logs/cascade_midway.log

# Khoj issues
tail -50 logs/khoj.log
```

**Verify patches:**
```bash
# Extension patches
python3 src/patch_windsurf_client.py --verify

# Binary patch
python3 src/patch_language_server_binary.py --verify
```

**Full system check:**
```bash
bash hg_status.sh
```

---

## ✅ Success Indicators

**Everything working when you see:**

1. **Proxy log:**
   ```
   [INFO] CONNECTION: POST /v1/chat/completions
   ```

2. **MITM log:**
   ```
   --- PROTOCOL EVENT ---
   {
     "timestamp": "2026-04-20...",
     "model": "...",
     "itemCount": ...
   }
   ```

3. **Network connections:**
   ```
   windsurf → 127.0.0.1:9999 (ESTABLISHED)
   ```

4. **No external connections** to Codeium IPs

---

**That's it! You're ready to use HIGH-GRAVITY with Windsurf!** 🎉
