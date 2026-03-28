#!/usr/bin/env python3
"""
Test all Gemini API keys for validity and capabilities
"""

import json
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

def test_key(api_key: str, key_index: int):
    """Test a single API key"""
    print(f"\n[{key_index}] Testing key: {api_key[:20]}...{api_key[-10:]}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m["name"] for m in models]
            
            veo_models = [m for m in model_names if "veo" in m.lower()]
            gemini_models = [m for m in model_names if "gemini" in m.lower()]
            
            print(f"    ✓ VALID - {len(models)} models")
            print(f"      Veo: {len(veo_models)}, Gemini: {len(gemini_models)}")
            
            if veo_models:
                print(f"      Veo models: {', '.join([m.split('/')[-1] for m in veo_models[:3]])}")
            
            return {
                "valid": True,
                "total_models": len(models),
                "veo_count": len(veo_models),
                "gemini_count": len(gemini_models),
                "veo_models": veo_models
            }
            
        elif response.status_code == 403:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            
            if "SERVICE_DISABLED" in str(error_data):
                print(f"    ✗ API DISABLED in project")
            elif "API key not valid" in error_msg:
                print(f"    ✗ INVALID KEY")
            else:
                print(f"    ✗ PERMISSION DENIED: {error_msg[:80]}")
            
            return {"valid": False, "error": "403", "message": error_msg}
            
        elif response.status_code == 429:
            print(f"    ✗ QUOTA EXCEEDED")
            return {"valid": False, "error": "429"}
            
        else:
            print(f"    ✗ HTTP {response.status_code}")
            return {"valid": False, "error": str(response.status_code)}
            
    except Exception as e:
        print(f"    ✗ ERROR: {e}")
        return {"valid": False, "error": str(e)}


def main():
    keys_file = REPO_ROOT / "config" / "gemini_keys.json"
    if not keys_file.exists():
        keys_file = REPO_ROOT / "gemini_keys.json"
    
    with open(keys_file) as f:
        data = json.load(f)
    
    keys = data["keys"]
    
    print("="*70)
    print("TESTING ALL GEMINI API KEYS")
    print("="*70)
    print(f"Total keys: {len(keys)}")
    
    results = []
    valid_keys = []
    veo_keys = []
    
    for i, key_data in enumerate(keys, 1):
        api_key = key_data["key"]
        result = test_key(api_key, i)
        result["index"] = i
        result["key"] = api_key
        results.append(result)
        
        if result.get("valid"):
            valid_keys.append(i)
            if result.get("veo_count", 0) > 0:
                veo_keys.append(i)
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Valid keys: {len(valid_keys)}/{len(keys)}")
    print(f"Keys with Veo access: {len(veo_keys)}")
    
    if valid_keys:
        print(f"\nValid key indices: {', '.join(map(str, valid_keys))}")
    
    if veo_keys:
        print(f"Veo-enabled key indices: {', '.join(map(str, veo_keys))}")
        print(f"\nRecommended key for Veo 3: #{veo_keys[0]}")
        print(f"  Key: {keys[veo_keys[0]-1]['key']}")
    
    # Save results
    output_file = REPO_ROOT / "key_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "test_date": "2026-03-02",
            "total_keys": len(keys),
            "valid_count": len(valid_keys),
            "veo_count": len(veo_keys),
            "results": results
        }, f, indent=2)
    
    print(f"\n[+] Results saved to: {output_file}")


if __name__ == "__main__":
    main()
