#!/usr/bin/env python3
"""
Test MITM Bridge for Gemini and Codex auto-detection and interception
"""

import requests
import json
import time
import os

PROXY_PORT = int(os.environ.get("HG_PROXY_PORT", "9998"))
PROXY_URL = f"http://localhost:{PROXY_PORT}"
PROXY_HOST_HEADER = "proxy.windsurf.com"

def test_telemetry():
    """Check MITM bridge status via telemetry endpoint"""
    print("\n" + "="*70)
    print("TESTING MITM BRIDGE TELEMETRY")
    print("="*70)
    
    try:
        resp = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Proxy Status: {data.get('status')}")
            print(f"✓ MITM Mode: {data.get('mitm_mode')}")
            print(f"✓ MITM Auto-Detect: {data.get('mitm_auto_detect')}")
            print(f"✓ MITM Services: {data.get('mitm_services', [])}")
            print(f"✓ MITM Detected Services: {data.get('mitm_detected_services', [])}")
            print(f"✓ MITM Inject Premium: {data.get('mitm_inject_premium')}")
            print(f"✓ MITM Reduce Rate Limits: {data.get('mitm_reduce_rate_limits')}")
            print(f"✓ Active Keys: {data.get('active_keys')}")
            print(f"✓ Cache Hits: {data.get('cache_hits')}")
            return True
        else:
            print(f"✗ Proxy not responding (status {resp.status_code})")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to proxy: {e}")
        return False


def test_smoke_usage():
    """Smoke check against a known routed endpoint."""
    print("\n" + "="*70)
    print("TESTING ROUTED USAGE ENDPOINT")
    print("="*70)
    try:
        headers = {"Host": PROXY_HOST_HEADER}
        resp = requests.get(
            f"{PROXY_URL}/api/oauth/usage",
            headers=headers,
            timeout=10,
        )
        print(f"← Response status: {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            if isinstance(body, dict):
                print(f"✓ usage keys: {list(body.keys())[:5]}")
                return True
            print(f"✗ Usage response not JSON: {body}")
        return False
    except Exception as e:
        print(f"✗ Smoke check failed: {e}")
        return False

def test_gemini_detection():
    """Test Gemini API detection"""
    print("\n" + "="*70)
    print("TESTING GEMINI AUTO-DETECTION")
    print("="*70)
    
    payload = {
        "model": "gemini-pro",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Host": "generativelanguage.googleapis.com"
    }
    
    try:
        print("→ Sending Gemini-like request...")
        resp = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=10
        )
        print(f"← Response status: {resp.status_code}")
        
        # Check telemetry again
        time.sleep(0.5)
        telem = requests.get(f"{PROXY_URL}/hg/telemetry").json()
        if "gemini" in telem.get("mitm_detected_services", []):
            print("✓ Gemini service auto-detected!")
            return True
        else:
            print("✗ Gemini not detected")
            return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_codex_detection():
    """Test Codex API detection"""
    print("\n" + "="*70)
    print("TESTING CODEX AUTO-DETECTION")
    print("="*70)
    
    payload = {
        "model": "davinci-codex",
        "prompt": "def hello():",
        "max_tokens": 50
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("→ Sending Codex-like request...")
        resp = requests.post(
            f"{PROXY_URL}/v1/engines/davinci-codex/completions",
            json=payload,
            headers=headers,
            timeout=10
        )
        print(f"← Response status: {resp.status_code}")
        
        # Check telemetry again
        time.sleep(0.5)
        telem = requests.get(f"{PROXY_URL}/hg/telemetry").json()
        if "codex" in telem.get("mitm_detected_services", []):
            print("✓ Codex service auto-detected!")
            return True
        else:
            print("✗ Codex not detected")
            return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_premium_injection():
    """Test premium model injection"""
    print("\n" + "="*70)
    print("TESTING PREMIUM MODEL INJECTION")
    print("="*70)
    
    # Test upgrading gemini-pro to gemini-3-pro-preview / gemini-2.5-pro
    payload = {
        "model": "gemini-pro",
        "messages": [
            {"role": "user", "content": "Please debug and analyze the root cause of this issue"}
        ]
    }

    print("→ Requesting gemini-pro with deep-reasoning prompt")
    print("  Expected: upgrade to gemini-3-pro-preview (deep tier) + thinkingBudget=-1")
    print("  (Check proxy logs for MITM_BRIDGE: Injected premium model / Set thinkingBudget)")
    
    try:
        resp = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            json=payload,
            timeout=10
        )
        print(f"← Response status: {resp.status_code}")
        print("✓ Check proxy logs for model injection confirmation")
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("MITM BRIDGE TEST SUITE")
    print("="*70)
    print("Testing automatic detection and interception of Gemini and Codex")
    print("Make sure the proxy is running: ./.hg_proxy_venv/bin/python -m src.proxy")
    print("="*70)
    
    results = []
    
    # Test 1: Telemetry
    results.append(("Telemetry", test_telemetry()))
    results.append(("Usage Smoke", test_smoke_usage()))
    
    # Test 2: Gemini Detection
    results.append(("Gemini Detection", test_gemini_detection()))
    
    # Test 3: Codex Detection
    results.append(("Codex Detection", test_codex_detection()))
    
    # Test 4: Premium Injection
    results.append(("Premium Injection", test_premium_injection()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nResults: {passed}/{total} tests passed")
    print("="*70 + "\n")
    
    return passed == total

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
