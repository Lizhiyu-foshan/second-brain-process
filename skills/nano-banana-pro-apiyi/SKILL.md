---
name: nano-banana-pro-apiyi
description: Generate or edit images via Gemini 3 Pro Image (Nano Banana Pro) using Google Official API or APIYI aggregation platform.
homepage: https://ai.google.dev/
metadata:
  {
    "openclaw":
      {
        "emoji": "🍌",
        "requires": { "bins": ["uv"], "env": ["GEMINI_API_KEY"] },
        "primaryEnv": "GEMINI_API_KEY",
        "install":
          [
            {
              "id": "uv-brew",
              "kind": "brew",
              "formula": "uv",
              "bins": ["uv"],
              "label": "Install uv (brew)",
            },
          ],
      },
  }
---

# Nano Banana Pro with APIYI Support

Generate or edit images via Gemini 3 Pro Image (Nano Banana Pro).

Supports:
- **Google Official API** (default)
- **APIYI Aggregation Platform** (apiyi.com) - Lower cost, no rate limits

## Quick Start

### Using Google Official API (default)

```bash
export GEMINI_API_KEY="your-google-api-key"

uv run generate_image.py --prompt "a cute cat on the moon" --filename "cat.png"
```

### Using APIYI Platform (Recommended - 80% cheaper)

```bash
export GEMINI_API_KEY="your-apiyi-key"

uv run generate_image.py --prompt "a cute cat on the moon" --filename "cat.png" --provider apiiyi
```

## Usage Examples

### Generate Image

```bash
# Default 1K resolution
uv run generate_image.py --prompt "sunset over mountains" --filename "sunset.png"

# 4K resolution
uv run generate_image.py --prompt "sunset over mountains" --filename "sunset.png" --resolution 4K

# With custom API key
uv run generate_image.py --prompt "sunset over mountains" --filename "sunset.png" --api-key YOUR_KEY
```

### Edit Image

```bash
# Single image edit
uv run generate_image.py --prompt "change background to Mars" --filename "output.png" -i "input.png"

# Multi-image composition (up to 14 images)
uv run generate_image.py --prompt "combine these into one scene" --filename "output.png" -i img1.png -i img2.png -i img3.png
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | API key for Google or APIYI | Yes |

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--prompt, -p` | Image description | Required |
| `--filename, -f` | Output filename | Required |
| `--resolution, -r` | Output resolution (1K/2K/4K) | 1K |
| `--provider` | API provider (google/apiiyi) | google |
| `--api-key, -k` | API key (overrides env var) | - |
| `--input-image, -i` | Input image(s) for editing | - |

## API Providers

### Google Official API
- **Pricing**: Standard Google pricing
- **Rate Limits**: Subject to Google quotas
- **Setup**: Get key from https://makersuite.google.com/app/apikey

### APIYI (apiyi.com) - Recommended
- **Pricing**: ~$0.05/image (80% cheaper)
- **Rate Limits**: No strict limits
- **Setup**: Register at https://apiyi.com, get API key
- **Benefits**: 
  - Lower cost
  - No Google Cloud setup needed
  - Supports multiple models

## Notes

- The script prints a `MEDIA:` line for OpenClaw to auto-attach on supported chat providers
- Use timestamps in filenames: `yyyy-mm-dd-hh-mm-ss-name.png`
- Resolutions: `1K` (default), `2K`, `4K`
