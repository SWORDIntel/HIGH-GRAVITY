# Veo 3.1 Video Generation Infrastructure

Complete infrastructure for submitting video generation jobs to Google's Veo 3.1 model using the extracted Gemini API keys.

## 📁 Files

- **`veo3_video_generator.py`** - Main video generation script
- **`gemini_keys.json`** - 18 Gemini API keys (1 with Veo access)
- **`example_prompts.txt`** - Example video prompts
- **`veo3_outputs/`** - Generated videos directory (auto-created)

## 🚀 Quick Start

### Single Video Generation
```bash
./veo3_video_generator.py --prompt "A cat playing piano in a jazz club"
```

### Batch Generation from File
```bash
./veo3_video_generator.py --prompts-file example_prompts.txt
```

### Custom Parameters
```bash
./veo3_video_generator.py \
  --prompt "Sunset over ocean waves" \
  --duration 8 \
  --aspect-ratio 16:9
```

## 📊 Features

### ✅ Multi-Key Rotation
- Automatically rotates through 18 available API keys
- Enables high-volume batch generation
- Prevents rate limiting on single key

### ✅ Job Monitoring
- Async job submission
- Automatic status polling (30s intervals)
- Progress tracking with ETA
- Auto-download on completion

### ✅ Batch Processing
- Process multiple prompts from file
- Parallel job submission
- Consolidated manifest output

### ✅ Error Handling
- Retry logic for failed requests
- Timeout protection (600s default)
- Detailed error reporting

## 🎬 Usage Examples

### Example 1: Single Video
```bash
./veo3_video_generator.py -p "Futuristic data center with glowing servers"
```

**Output**:
```
[*] Submitting job: Futuristic data center with glowing servers...
[+] Job submitted: models/veo-3.1-generate-preview/operations/abc123
[*] Monitoring 1 jobs...
    complete     - Futuristic data center with glowing servers
[*] Downloading video...
[+] Downloaded: veo3_outputs/veo3_20260302_145300_Futuristic_data_center.mp4
```

### Example 2: Batch from File
```bash
# Create prompts file
cat > my_prompts.txt <<EOF
Cybersecurity analyst at work
Network traffic visualization
Server room time-lapse
EOF

# Generate all videos
./veo3_video_generator.py -f my_prompts.txt
```

### Example 3: No Auto-Monitor (Submit and Exit)
```bash
./veo3_video_generator.py -f prompts.txt --no-monitor
```

## 📋 Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--prompt` | `-p` | Single video prompt | - |
| `--prompts-file` | `-f` | File with prompts (one per line) | - |
| `--duration` | `-d` | Video duration in seconds | 8 |
| `--aspect-ratio` | `-a` | Video aspect ratio | 16:9 |
| `--no-monitor` | - | Don't monitor jobs after submission | False |
| `--keys-file` | `-k` | Path to gemini_keys.json | auto-detect |

## 🎨 Supported Aspect Ratios

- `16:9` - Widescreen (default)
- `9:16` - Vertical/mobile
- `1:1` - Square
- `4:3` - Classic
- `21:9` - Ultrawide

## ⏱️ Video Duration

- Minimum: 2 seconds
- Maximum: 8 seconds (Veo 3.1 preview limit)
- Default: 8 seconds

## 📦 Output Structure

```
veo3_outputs/
├── veo3_20260302_145300_Futuristic_data_center.mp4
├── veo3_20260302_145315_Cybersecurity_analyst.mp4
├── veo3_20260302_145330_Network_traffic_visual.mp4
└── manifest_1709391600.json
```

### Manifest Format
```json
{
  "generated_at": "2026-03-02T14:53:00Z",
  "total_jobs": 3,
  "completed": [
    {
      "prompt": "Futuristic data center...",
      "operation_name": "models/veo-3.1-generate-preview/operations/abc123",
      "output_file": "veo3_outputs/veo3_20260302_145300_Futuristic_data_center.mp4",
      "status": "complete"
    }
  ],
  "failed": [],
  "pending": []
}
```

## 🔑 API Key Management

### Key Rotation Strategy
The script uses round-robin rotation across all 18 keys:
1. Job 1 → Key 1
2. Job 2 → Key 2
3. ...
4. Job 19 → Key 1 (wraps around)

### Key with Veo Access
**Key**: `AIzaSyD0A0rw0QD0iVkVb7EJnD_AKVU5Lv4ryQw`
- ✅ Confirmed Veo 3.1 access
- 10 existing generated files
- Files expire ~48 hours after creation

### Adding More Keys
Edit `gemini_keys.json`:
```json
{
  "keys": [
    {
      "key": "AIzaSy...",
      "endpoint": "https://generativelanguage.googleapis.com/v1beta/files",
      "status": "active"
    }
  ]
}
```

## 🛠️ Advanced Usage

### Python API
```python
from veo3_video_generator import Veo3VideoGenerator

# Initialize
gen = Veo3VideoGenerator()

# Submit single job
job = gen.submit_video_job("A cat playing piano", duration=8)

# Batch generate
prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
gen.batch_generate(prompts, monitor=True)

# Manual monitoring
gen.monitor_jobs(check_interval=30, timeout=600)

# Download completed videos
for job in gen.completed:
    gen.download_video(job)
```

### Custom Monitoring Loop
```python
gen = Veo3VideoGenerator()

# Submit jobs without monitoring
gen.batch_generate(prompts, monitor=False)

# Custom monitoring
while gen.jobs:
    for job in gen.jobs:
        status = gen.check_job_status(job)
        print(f"Job {job['operation_name']}: {status}")
    time.sleep(60)  # Check every minute
```

## 📊 Rate Limits & Quotas

### Per Key Limits (Estimated)
- **Requests/minute**: ~10
- **Requests/day**: ~1000
- **Concurrent jobs**: ~5

### With 18 Keys
- **Effective rate**: ~180 req/min
- **Daily capacity**: ~18,000 videos
- **Concurrent jobs**: ~90

## 🐛 Troubleshooting

### "No video file URI found"
- Job completed but video not accessible
- Check job manifest for error details
- Verify API key has Veo access

### "Submission failed: 429"
- Rate limit exceeded
- Script will auto-rotate to next key
- Reduce submission rate or add more keys

### "Timeout reached"
- Video generation taking >10 minutes
- Increase timeout: modify `monitor_jobs(timeout=1200)`
- Check job status manually later

### Videos Not Downloading
- Ensure job status is "complete"
- Check network connectivity
- Verify download URI in job result

## 📈 Performance Tips

1. **Batch Processing**: Submit all jobs first, then monitor
2. **Key Rotation**: Use all 18 keys for maximum throughput
3. **Parallel Downloads**: Download videos as they complete
4. **Prompt Optimization**: Clear, detailed prompts generate faster

## 🔒 Security Notes

- API keys stored in `gemini_keys.json`
- Keys have limited scope (Gemini API only)
- Generated videos expire after ~48 hours
- Download videos promptly for archival

## 📝 Example Workflow

```bash
# 1. Create prompts file
cat > research_videos.txt <<EOF
Visualization of neural network training
3D render of quantum computer components
Animation of blockchain transaction flow
EOF

# 2. Generate videos
./veo3_video_generator.py -f research_videos.txt -d 8 -a 16:9

# 3. Check outputs
ls -lh veo3_outputs/

# 4. Review manifest
cat veo3_outputs/manifest_*.json | jq '.completed | length'
```

## 🎯 Use Cases

- **Research Visualization**: Generate explanatory videos
- **Presentation Content**: Create B-roll footage
- **Concept Prototyping**: Visualize ideas quickly
- **Training Data**: Generate synthetic video datasets
- **Marketing**: Produce promotional content

## 📚 Resources

- [Veo 3 Documentation](https://ai.google.dev/gemini-api/docs/veo)
- [Gemini API Reference](https://ai.google.dev/api)
- [Video Generation Best Practices](https://ai.google.dev/gemini-api/docs/video-generation)

## 🔄 Updates

**v1.0** (2026-03-02)
- Initial release
- 18 API keys
- Batch processing
- Auto-monitoring
- Download management
