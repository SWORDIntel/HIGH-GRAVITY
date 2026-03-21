# Veo 3.1 Guide

Main files:

- [scripts/veo3_video_generator.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/veo3_video_generator.py)
- [scripts/check_video_status.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/check_video_status.py)
- [scripts/test_veo3.sh](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/test_veo3.sh)
- [examples/example_prompts.txt](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/examples/example_prompts.txt)

## Key file

The Veo scripts look for keys in:

1. `config/gemini_keys.json`
2. `gemini_keys.json`

Use [config/gemini_keys.example.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.example.json) as the template, or update [config/gemini_keys.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.json) directly.

## Quick start

Single prompt:

```bash
python3 scripts/veo3_video_generator.py \
  --prompt "A cat playing piano in a jazz club"
```

Batch from file:

```bash
python3 scripts/veo3_video_generator.py \
  --prompts-file examples/example_prompts.txt
```

Custom parameters:

```bash
python3 scripts/veo3_video_generator.py \
  --prompt "Sunset over ocean waves" \
  --duration 8 \
  --aspect-ratio 16:9
```

## Outputs

Generated files go to:

- `veo3_outputs/`

Typical files:

- `veo3_outputs/*.mp4`
- `veo3_outputs/manifest_*.json`

## Test script

Quick smoke test:

```bash
bash scripts/test_veo3.sh
```

## Notes

- `veo3_outputs/` is generated at runtime and is git-ignored.
- `key_test_results.json` is generated output from key testing and is git-ignored.
