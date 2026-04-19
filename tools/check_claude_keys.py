#!/usr/bin/env python3
"""
Claude API Key Checker
Validates all Claude keys from docs/roadmap/claude.md
"""
import re
import sys
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_FILE = REPO_ROOT / "docs" / "roadmap" / "claude.md"
OUTPUT_FILE = REPO_ROOT / "config" / "claude_keys.json"

def extract_keys(file_path):
    """Extract unique Claude API keys from file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    keys = re.findall(r'sk-ant-api03-[A-Za-z0-9_-]+', content)
    return list(set(keys))

def check_key(api_key, index, total):
    """Check if a Claude API key is valid"""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Simple test: try to list models or make a minimal request
    test_payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        status = "active" if response.status_code in [200, 201] else "invalid"
        error = None if status == "active" else response.text[:200]
        
        print(f"[{index}/{total}] {api_key[:20]}... - {status}")
        
        return {
            "key": api_key,
            "status": status,
            "status_code": response.status_code,
            "error": error,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"[{index}/{total}] {api_key[:20]}... - ERROR: {str(e)[:50]}")
        return {
            "key": api_key,
            "status": "error",
            "error": str(e)[:200],
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

def main():
    print("=" * 70)
    print("CLAUDE API KEY CHECKER")
    print("=" * 70)
    
    # Extract keys
    print(f"\n[*] Extracting keys from {CLAUDE_FILE}")
    keys = extract_keys(CLAUDE_FILE)
    print(f"[+] Found {len(keys)} unique keys")
    
    # Check keys in parallel
    print(f"\n[*] Checking keys (this may take a while)...")
    results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(check_key, key, i+1, len(keys)): key 
            for i, key in enumerate(keys)
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            time.sleep(0.5)  # Rate limiting
    
    # Summary
    active = sum(1 for r in results if r["status"] == "active")
    invalid = sum(1 for r in results if r["status"] == "invalid")
    errors = sum(1 for r in results if r["status"] == "error")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total keys:    {len(results)}")
    print(f"Active:        {active}")
    print(f"Invalid:       {invalid}")
    print(f"Errors:        {errors}")
    
    # Save results
    import json
    output_data = {
        "service": "anthropic_claude",
        "total_keys": len(results),
        "active_keys": active,
        "invalid_keys": invalid,
        "error_keys": errors,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "keys": results
    }
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n[+] Results saved to {OUTPUT_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    main()
