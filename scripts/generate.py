#!/usr/bin/env python3
"""generate.py — generate or edit images via Google Gemini Nano Banana 2.

Stdlib-only CLI. Saves a PNG plus a JSON sidecar with the prompt and config
so you can reproduce or iterate.

Usage:
    python generate.py "prompt text"
    python generate.py "prompt" --aspect 16:9 --resolution 2K
    python generate.py "edit instructions" --image input.png
    python generate.py "..." --image ref1.png --image ref2.png
    python generate.py "..." --output path/to/out.png
    python generate.py - <<< "long prompt from stdin"

Exit codes:
    0 success
    1 API/HTTP/network error
    2 bad arguments or missing API key
    3 no image returned (often a safety refusal)
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "gemini-3.1-flash-image-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

VALID_ASPECTS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
}
VALID_RESOLUTIONS = {"512", "1K", "2K", "4K"}


def resolve_api_key() -> str:
    """env var → ./.env → ~/.env. Exits 2 if not found."""
    if k := os.environ.get("GEMINI_API_KEY"):
        return k.strip()
    for env_file in [Path.cwd() / ".env", Path.home() / ".env"]:
        if not env_file.is_file():
            continue
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if not line.startswith("GEMINI_API_KEY") or "=" not in line:
                continue
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                return val
    sys.stderr.write("error: GEMINI_API_KEY not found in env, ./.env, or ~/.env\n")
    sys.exit(2)


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len] or "image"


def load_image_b64(path: str) -> tuple[str, str]:
    p = Path(path)
    if not p.is_file():
        sys.stderr.write(f"error: input image not found: {path}\n")
        sys.exit(2)
    ext = p.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp"}.get(ext)
    if not mime:
        sys.stderr.write(f"error: unsupported image type .{ext} (use png/jpg/webp)\n")
        sys.exit(2)
    return mime, base64.b64encode(p.read_bytes()).decode()


def build_payload(prompt: str, aspect: str, resolution: str, images: list) -> dict:
    parts = [{"text": prompt}]
    for img_path in images:
        mime, data = load_image_b64(img_path)
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect,
                "imageSize": resolution,
            },
        },
    }


def call_api(payload: dict, api_key: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"error: HTTP {e.code} from Gemini API\n{body}\n")
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"error: network error: {e.reason}\n")
        sys.exit(1)


EXT_FOR_MIME = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def extract(resp: dict) -> tuple:
    text_parts = []
    img_bytes = None
    mime = "image/png"
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            if "text" in part and part["text"]:
                text_parts.append(part["text"])
            elif "inlineData" in part:
                mime = part["inlineData"].get("mimeType", "image/png")
                img_bytes = base64.b64decode(part["inlineData"]["data"])
    return img_bytes, "\n".join(text_parts).strip(), mime


def main():
    ap = argparse.ArgumentParser(
        description="Generate images via Google Gemini Nano Banana 2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("prompt", help='Prompt text. Use "-" to read from stdin.')
    ap.add_argument("--aspect", default="1:1",
                    help=f"Aspect ratio (default 1:1). Choices: {', '.join(sorted(VALID_ASPECTS))}")
    ap.add_argument("--resolution", default="1K",
                    help=f"Image size (default 1K). Choices: {', '.join(sorted(VALID_RESOLUTIONS))}")
    ap.add_argument("--image", action="append", default=[],
                    help="Input/reference image. Pass multiple times for multi-reference.")
    ap.add_argument("--output", help="Output PNG path. Default: ./generated-images/<ts>-<slug>.png")
    ap.add_argument("--no-sidecar", action="store_true", help="Skip writing the .json sidecar.")
    args = ap.parse_args()

    if args.aspect not in VALID_ASPECTS:
        sys.stderr.write(f"error: invalid --aspect '{args.aspect}'. Choices: {sorted(VALID_ASPECTS)}\n")
        sys.exit(2)
    if args.resolution not in VALID_RESOLUTIONS:
        sys.stderr.write(
            f"error: invalid --resolution '{args.resolution}'. "
            f"Use 512, 1K, 2K, or 4K (capital K).\n"
        )
        sys.exit(2)

    prompt = sys.stdin.read() if args.prompt == "-" else args.prompt
    prompt = prompt.strip()
    if not prompt:
        sys.stderr.write("error: empty prompt\n")
        sys.exit(2)

    api_key = resolve_api_key()
    payload = build_payload(prompt, args.aspect, args.resolution, args.image)
    resp = call_api(payload, api_key)
    img_bytes, text, mime = extract(resp)

    if img_bytes is None:
        sys.stderr.write("error: no image returned by the API.\n")
        if text:
            sys.stderr.write(f"model said: {text}\n")
        sys.exit(3)

    actual_ext = EXT_FOR_MIME.get(mime, "bin")
    if args.output:
        out_path = Path(args.output)
        requested = out_path.suffix.lower().lstrip(".")
        if requested == "jpeg":
            requested = "jpg"
        if requested in EXT_FOR_MIME.values() and requested != actual_ext:
            new_path = out_path.with_suffix(f".{actual_ext}")
            sys.stderr.write(
                f"note: Gemini returned {mime}; saving as {new_path} "
                f"(your --output asked for .{requested}, but the API doesn't honor a format request).\n"
            )
            out_path = new_path
    else:
        ts = time.strftime("%Y%m%d-%H%M%S")
        out_path = Path("generated-images") / f"{ts}-{slugify(prompt)}.{actual_ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_bytes)

    if not args.no_sidecar:
        sidecar = out_path.with_suffix(".json")
        sidecar.write_text(json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "aspect_ratio": args.aspect,
            "resolution": args.resolution,
            "input_images": args.image,
            "model_text": text,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, indent=2))

    print(str(out_path))
    if text:
        sys.stderr.write(f"\n[model commentary]\n{text}\n")


if __name__ == "__main__":
    main()
