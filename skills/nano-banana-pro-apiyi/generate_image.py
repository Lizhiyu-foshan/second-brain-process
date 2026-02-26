#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
#     "requests>=2.30.0",
# ]
# ///
"""
Generate images using Nano Banana Pro (Gemini 3 Pro Image) API.
Supports Google Official API and APIYI (apiyi.com) aggregation platform.

Usage:
    # Google Official API (default)
    uv run generate_image.py --prompt "your image description" --filename "output.png"
    
    # APIYI Platform
    uv run generate_image.py --prompt "your image description" --filename "output.png" --provider apiiyi
    
    # With custom API key
    uv run generate_image.py --prompt "your image description" --filename "output.png" --api-key YOUR_KEY

Multi-image editing (up to 14 images):
    uv run generate_image.py --prompt "combine these images" --filename "output.png" -i img1.png -i img2.png

Environment Variables:
    GEMINI_API_KEY: API key for Google Official or APIYI
    GEMINI_BASE_URL: Custom base URL (default: https://api.apiyi.com/v1 for APIYI)
"""

import argparse
import os
import sys
import base64
import requests
from pathlib import Path
from io import BytesIO


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def get_base_url(provider: str, custom_url: str | None) -> str:
    """Get base URL based on provider."""
    if custom_url:
        return custom_url
    
    if provider == "apiiyi":
        return "https://api.apiyi.com/v1"
    
    # Google official default (google-genai handles this internally)
    return None


def generate_image_google_official(api_key: str, prompt: str, input_images: list, resolution: str, output_path: Path):
    """Generate image using Google Official API."""
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage
    
    client = genai.Client(api_key=api_key)
    
    # Load input images if provided
    contents = []
    if input_images:
        for img_path in input_images:
            img = PILImage.open(img_path)
            contents.append(img)
        contents.append(prompt)
    else:
        contents = prompt
    
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                image_size=resolution
            )
        )
    )
    
    return response


def generate_image_apiiyi(api_key: str, prompt: str, input_images: list, resolution: str, output_path: Path):
    """Generate image using APIYI platform (OpenAI compatible format)."""
    from PIL import Image as PILImage
    
    base_url = "https://api.apiyi.com/v1"
    
    # Prepare messages
    messages = []
    content = []
    
    # Add input images if provided
    if input_images:
        for img_path in input_images:
            with open(img_path, "rb") as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}"
                    }
                })
    
    # Add text prompt
    content.append({
        "type": "text",
        "text": prompt
    })
    
    messages.append({
        "role": "user",
        "content": content
    })
    
    # Map resolution to size
    size_map = {
        "1K": "1024x1024",
        "2K": "2048x2048", 
        "4K": "4096x4096"
    }
    
    # API call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gemini-3-pro-image-preview",
        "messages": messages,
        "size": size_map.get(resolution, "1024x1024")
    }
    
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=300
    )
    
    response.raise_for_status()
    return response.json()


def save_image_from_response(response, provider: str, output_path: Path):
    """Extract and save image from API response."""
    from PIL import Image as PILImage
    
    image_saved = False
    
    if provider == "apiiyi":
        # APIYI OpenAI format
        if "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0]["message"]
            if "content" in message:
                content = message["content"]
                
                # Check if content is a Markdown image format: ![image](data:image/jpeg;base64,...)
                if isinstance(content, str) and content.startswith("![image](data:image"):
                    import re
                    # Extract base64 data from markdown
                    match = re.search(r'data:image/[^;]+;base64,([^)]+)', content)
                    if match:
                        base64_data = match.group(1)
                        image_data = base64.b64decode(base64_data)
                        image = PILImage.open(BytesIO(image_data))
                        _save_image(image, output_path)
                        image_saved = True
                
                # Check if content is a list (multimodal)
                elif isinstance(content, list):
                    for item in content:
                        if item.get("type") == "image_url":
                            image_url = item["image_url"]["url"]
                            if image_url.startswith("data:image"):
                                # Extract base64 data
                                base64_data = image_url.split(",")[1]
                                image_data = base64.b64decode(base64_data)
                                image = PILImage.open(BytesIO(image_data))
                                _save_image(image, output_path)
                                image_saved = True
                                break
    else:
        # Google Official format
        from google.genai import types
        
        for part in response.parts:
            if part.text is not None:
                print(f"Model response: {part.text}")
            elif part.inline_data is not None:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                
                image = PILImage.open(BytesIO(image_data))
                _save_image(image, output_path)
                image_saved = True
    
    return image_saved


def _save_image(image, output_path: Path):
    """Save PIL Image to file."""
    # Ensure RGB mode for PNG
    if image.mode == 'RGBA':
        rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])
        rgb_image.save(str(output_path), 'PNG')
    elif image.mode == 'RGB':
        image.save(str(output_path), 'PNG')
    else:
        image.convert('RGB').save(str(output_path), 'PNG')


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image) - Supports Google Official & APIYI"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        dest="input_images",
        metavar="IMAGE",
        help="Input image path(s) for editing/composition. Can be specified multiple times (up to 14 images)."
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="API key (overrides GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--provider",
        choices=["google", "apiiyi"],
        default="google",
        help="API provider: google (official) or apiiyi (aggregation platform, default: google)"
    )
    parser.add_argument(
        "--base-url",
        help="Custom base URL (overrides provider default)"
    )

    args = parser.parse_args()

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Set up output path
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate input images
    if args.input_images and len(args.input_images) > 14:
        print(f"Error: Too many input images ({len(args.input_images)}). Maximum is 14.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.provider == "apiiyi":
            print(f"Generating image via APIYI with resolution {args.resolution}...")
            response = generate_image_apiiyi(
                api_key=api_key,
                prompt=args.prompt,
                input_images=args.input_images,
                resolution=args.resolution,
                output_path=output_path
            )
        else:
            print(f"Generating image via Google Official API with resolution {args.resolution}...")
            response = generate_image_google_official(
                api_key=api_key,
                prompt=args.prompt,
                input_images=args.input_images,
                resolution=args.resolution,
                output_path=output_path
            )
        
        # Save image
        image_saved = save_image_from_response(response, args.provider, output_path)
        
        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
            # OpenClaw parses MEDIA tokens and will attach the file on supported providers.
            print(f"MEDIA: {full_path}")
        else:
            print("Error: No image was generated in the response.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
