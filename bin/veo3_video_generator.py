#!/usr/bin/env python3
"""
Veo 3.1 Video Generation Infrastructure
========================================

Submit video generation jobs to Google's Veo 3.1 model using Gemini API keys.
Supports batch processing, job monitoring, and automatic download.

Features:
- Multi-key rotation for high-volume generation
- Async job submission and monitoring
- Automatic video download
- Progress tracking and status reporting
- Error handling and retry logic
"""

import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading
from queue import Queue

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

class Veo3VideoGenerator:
    def __init__(self, keys_file: str = None):
        """Initialize with Gemini API keys"""
        if keys_file is None:
            keys_file = self._default_keys_file()
        
        self.keys_file = Path(keys_file)
        self.keys = self._load_keys()
        self.current_key_idx = 0
        self.output_dir = REPO_ROOT / "veo3_outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Job tracking
        self.jobs = []
        self.completed = []
        self.failed = []
        
    def _load_keys(self) -> List[Dict]:
        """Load API keys from JSON file"""
        with open(self.keys_file) as f:
            data = json.load(f)
        return data["keys"]

    def _default_keys_file(self) -> Path:
        """Find the preferred local keys file"""
        candidates = [
            REPO_ROOT / "config" / "gemini_keys.json",
            REPO_ROOT / "gemini_keys.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]
    
    def _get_next_key(self) -> str:
        """Round-robin key selection"""
        key = self.keys[self.current_key_idx]["key"]
        self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
        return key
    
    def submit_video_job(self, prompt: str, duration: int = 8, 
                        aspect_ratio: str = "16:9") -> Optional[Dict]:
        """
        Submit a video generation job to Veo 3.1
        
        Args:
            prompt: Text description of video to generate
            duration: Video duration in seconds (default: 8)
            aspect_ratio: Video aspect ratio (default: 16:9)
            
        Returns:
            Job info dict with operation name and metadata
        """
        api_key = self._get_next_key()
        
        # Veo 3.1 generation endpoint (uses predictLongRunning method)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key={api_key}"
        
        payload = {
            "instances": [{
                "prompt": prompt
            }]
        }
        
        try:
            print(f"[*] Submitting job: {prompt[:60]}...")
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract operation name from response
                operation_name = None
                if "name" in result:
                    operation_name = result["name"]
                elif "metadata" in result and "name" in result["metadata"]:
                    operation_name = result["metadata"]["name"]
                
                job_info = {
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "operation_name": operation_name,
                    "api_key": api_key,
                    "submitted_at": datetime.now().isoformat(),
                    "status": "submitted",
                    "response": result
                }
                
                self.jobs.append(job_info)
                print(f"[+] Job submitted: {operation_name}")
                return job_info
                
            else:
                print(f"[!] Submission failed: {response.status_code}")
                print(f"    Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"[!] Error submitting job: {e}")
            return None
    
    def check_job_status(self, job: Dict) -> str:
        """
        Check status of a video generation job
        
        Returns:
            Status string: 'processing', 'complete', 'failed'
        """
        if not job.get("operation_name"):
            return "failed"
        
        api_key = job["api_key"]
        operation_name = job["operation_name"]
        
        # Check operation status
        url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("done"):
                    if "error" in result:
                        job["status"] = "failed"
                        job["error"] = result["error"]
                        return "failed"
                    else:
                        job["status"] = "complete"
                        job["result"] = result
                        return "complete"
                else:
                    job["status"] = "processing"
                    return "processing"
            else:
                return "unknown"
                
        except Exception as e:
            print(f"[!] Error checking status: {e}")
            return "unknown"
    
    def download_video(self, job: Dict) -> Optional[str]:
        """
        Download completed video file
        
        Returns:
            Path to downloaded video file
        """
        if job["status"] != "complete":
            print(f"[!] Job not complete: {job['status']}")
            return None
        
        # Extract file info from result
        result = job.get("result", {})
        response = result.get("response", {})
        
        # Try to find video file reference
        file_uri = None
        file_name = None
        
        # Check various possible locations
        if "candidates" in response:
            for candidate in response["candidates"]:
                if "content" in candidate:
                    parts = candidate["content"].get("parts", [])
                    for part in parts:
                        if "fileData" in part:
                            file_uri = part["fileData"].get("fileUri")
                            file_name = part["fileData"].get("mimeType", "video.mp4")
        
        if not file_uri:
            # Try alternate structure
            if "file" in response:
                file_uri = response["file"].get("uri")
                file_name = response["file"].get("name", "video.mp4")
        
        if not file_uri:
            print("[!] No video file URI found in response")
            return None
        
        # Download the file
        api_key = job["api_key"]
        download_url = f"{file_uri}:download?alt=media&key={api_key}"
        
        try:
            print(f"[*] Downloading video...")
            response = requests.get(download_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                # Generate output filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_prompt = "".join(c for c in job["prompt"][:30] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_prompt = safe_prompt.replace(' ', '_')
                output_file = self.output_dir / f"veo3_{timestamp}_{safe_prompt}.mp4"
                
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                job["output_file"] = str(output_file)
                print(f"[+] Downloaded: {output_file}")
                return str(output_file)
            else:
                print(f"[!] Download failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[!] Error downloading video: {e}")
            return None
    
    def monitor_jobs(self, check_interval: int = 30, timeout: int = 600):
        """
        Monitor all submitted jobs until completion or timeout
        
        Args:
            check_interval: Seconds between status checks
            timeout: Maximum seconds to wait for completion
        """
        start_time = time.time()
        
        print(f"\n[*] Monitoring {len(self.jobs)} jobs...")
        print(f"    Check interval: {check_interval}s")
        print(f"    Timeout: {timeout}s")
        
        while self.jobs:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print(f"\n[!] Timeout reached ({timeout}s)")
                break
            
            print(f"\n[*] Status check (elapsed: {elapsed:.0f}s)")
            
            for job in self.jobs[:]:  # Copy list to allow removal
                status = self.check_job_status(job)
                
                prompt_preview = job["prompt"][:40]
                print(f"    {status:12s} - {prompt_preview}")
                
                if status == "complete":
                    self.jobs.remove(job)
                    self.completed.append(job)
                    
                    # Auto-download
                    self.download_video(job)
                    
                elif status == "failed":
                    self.jobs.remove(job)
                    self.failed.append(job)
            
            if self.jobs:
                print(f"\n[*] Waiting {check_interval}s before next check...")
                time.sleep(check_interval)
            else:
                print("\n[+] All jobs completed!")
                break
        
        # Summary
        print(f"\n{'='*70}")
        print(f"GENERATION SUMMARY")
        print(f"{'='*70}")
        print(f"Completed: {len(self.completed)}")
        print(f"Failed: {len(self.failed)}")
        print(f"Pending: {len(self.jobs)}")
        print(f"{'='*70}\n")
    
    def batch_generate(self, prompts: List[str], duration: int = 8,
                      aspect_ratio: str = "16:9", monitor: bool = True):
        """
        Generate multiple videos from a list of prompts
        
        Args:
            prompts: List of text prompts
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio
            monitor: Whether to monitor jobs until completion
        """
        print(f"\n{'='*70}")
        print(f"VEO 3.1 BATCH VIDEO GENERATION")
        print(f"{'='*70}")
        print(f"Prompts: {len(prompts)}")
        print(f"Duration: {duration}s")
        print(f"Aspect ratio: {aspect_ratio}")
        print(f"Available keys: {len(self.keys)}")
        print(f"{'='*70}\n")
        
        # Submit all jobs
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] Submitting...")
            self.submit_video_job(prompt, duration, aspect_ratio)
            
            # Brief delay between submissions
            if i < len(prompts):
                time.sleep(2)
        
        # Monitor if requested
        if monitor:
            self.monitor_jobs()
        
        # Save job manifest
        self.save_manifest()
    
    def save_manifest(self):
        """Save job manifest to JSON"""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "total_jobs": len(self.jobs) + len(self.completed) + len(self.failed),
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.jobs
        }
        
        manifest_file = self.output_dir / f"manifest_{int(time.time())}.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"[+] Manifest saved: {manifest_file}")


def main():
    parser = argparse.ArgumentParser(description="Veo 3.1 Video Generation")
    parser.add_argument("--prompt", "-p", help="Single video prompt")
    parser.add_argument("--prompts-file", "-f", help="File with prompts (one per line)")
    parser.add_argument("--duration", "-d", type=int, default=8, help="Video duration in seconds (default: 8)")
    parser.add_argument("--aspect-ratio", "-a", default="16:9", help="Aspect ratio (default: 16:9)")
    parser.add_argument("--no-monitor", action="store_true", help="Don't monitor jobs")
    parser.add_argument("--keys-file", "-k", help="Path to a keys file, usually config/gemini_keys.json")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = Veo3VideoGenerator(keys_file=args.keys_file)
    
    # Collect prompts
    prompts = []
    
    if args.prompt:
        prompts.append(args.prompt)
    
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts.extend([line.strip() for line in f if line.strip()])
    
    if not prompts:
        print("[!] No prompts provided. Use --prompt or --prompts-file")
        print("\nExample usage:")
        print("  # Single video")
        print("  python3 scripts/veo3_video_generator.py --prompt 'A cat playing piano'")
        print("")
        print("  # Batch from file")
        print("  python3 scripts/veo3_video_generator.py --prompts-file examples/example_prompts.txt")
        print("")
        print("  # Custom duration and aspect ratio")
        print("  python3 scripts/veo3_video_generator.py -p 'Sunset over ocean' -d 8 -a 16:9")
        sys.exit(1)
    
    # Generate videos
    generator.batch_generate(
        prompts=prompts,
        duration=args.duration,
        aspect_ratio=args.aspect_ratio,
        monitor=not args.no_monitor
    )


if __name__ == "__main__":
    main()
