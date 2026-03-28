#!/usr/bin/env python3
"""
Veo 3 Video Status Checker
===========================

Check status of Veo 3 video generation jobs and download completed videos.
"""

import sys
import json
import requests
import argparse
from pathlib import Path

def check_video_status(operation_id: str, api_key: str):
    """Check status of a Veo 3 video generation job"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{operation_id}?key={api_key}"
    
    print(f"[*] Checking video generation status...")
    print(f"    Operation: {operation_id}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n[+] Status retrieved successfully")
            print(json.dumps(data, indent=2))
            
            # Check if done
            if data.get("done"):
                print(f"\n[+] Video generation COMPLETE!")
                
                # Extract video URI
                response_data = data.get("response", {})
                generate_response = response_data.get("generateVideoResponse", {})
                samples = generate_response.get("generatedSamples", [])
                
                if samples:
                    video_uri = samples[0].get("video", {}).get("uri")
                    
                    if video_uri:
                        print(f"[+] Video URI: {video_uri}")
                        return video_uri
                    else:
                        print(f"[!] No video URI found in response")
                else:
                    print(f"[!] No generated samples found")
            else:
                print(f"\n[*] Video generation still PROCESSING...")
                
        else:
            print(f"[!] Request failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"[!] Error: {e}")
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Check Veo 3 video status")
    parser.add_argument("operation_id", help="Operation ID (e.g., models/veo-3.1-generate-preview/operations/xxx)")
    parser.add_argument("--api-key", "-k", default="AIzaSyD0A0rw0QD0iVkVb7EJnD_AKVU5Lv4ryQw", help="API key")
    parser.add_argument("--download", "-d", help="Download to specified file")
    
    args = parser.parse_args()
    
    video_uri = check_video_status(args.operation_id, args.api_key)
    
    if video_uri and args.download:
        print(f"\n[*] Downloading video to {args.download}...")
        
        # Note: Direct download may not work, URI might be for metadata only
        print(f"[!] Note: You may need to access this URI in a browser:")
        print(f"    {video_uri}")


if __name__ == "__main__":
    main()
