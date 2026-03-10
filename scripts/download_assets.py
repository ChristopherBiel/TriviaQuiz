#!/usr/bin/env python3
"""Download self-hosted static assets for GDPR compliance.

Fetches Tailwind CDN JS and Inter font files so no third-party servers
receive visitor IP addresses at page-load time.

Usage:
    python scripts/download_assets.py        # from project root
    python download_assets.py                # from scripts/ directory
"""
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

# Use certifi CA bundle when available (needed on macOS dev environments).
# In Docker/Linux the default SSL context works fine without it.
try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Resolve project root regardless of cwd
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Only download latin and latin-ext — sufficient for German and Western-European text
KEEP_SUBSETS = {"latin", "latin-ext"}


def fetch(url: str, ua: str | None = None) -> bytes:
    req = urllib.request.Request(url)
    if ua:
        req.add_header("User-Agent", ua)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as r:
            return r.read()
    except urllib.error.URLError as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)


def download_tailwind() -> None:
    dest_dir = os.path.join(BASE_DIR, "static", "js")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "tailwind.cdn.js")
    print("Downloading Tailwind CDN JS...")
    data = fetch("https://cdn.tailwindcss.com", ua=UA)
    with open(dest, "wb") as f:
        f.write(data)
    print(f"  {len(data):,} bytes → static/js/tailwind.cdn.js")


def download_inter_fonts() -> None:
    font_dir = os.path.join(BASE_DIR, "static", "fonts")
    css_dir = os.path.join(BASE_DIR, "static", "css")
    os.makedirs(font_dir, exist_ok=True)
    os.makedirs(css_dir, exist_ok=True)

    google_url = (
        "https://fonts.googleapis.com/css2"
        "?family=Inter:wght@400;500;600;700&display=swap"
    )
    print("Fetching Inter font metadata from Google Fonts...")
    css = fetch(google_url, ua=UA).decode("utf-8")

    # Google Fonts CSS has a comment before each @font-face block: /* latin */ etc.
    blocks = re.findall(
        r"/\*\s*([^*]+?)\s*\*/\s*@font-face\s*\{([^}]+)\}", css, re.DOTALL
    )

    local_faces: list[tuple[int, str, str, str]] = []  # (weight, subset, filename, unicode_range)
    # Maps remote URL → local filename so that variable fonts (where multiple
    # weights share one woff2 file) are downloaded only once but referenced correctly.
    url_to_filename: dict[str, str] = {}

    for subset_comment, block in blocks:
        subset = subset_comment.strip()
        if subset not in KEEP_SUBSETS:
            continue

        weight_m = re.search(r"font-weight:\s*(\d+)", block)
        url_m = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        unicode_m = re.search(r"unicode-range:\s*([^;]+);", block)

        if not (weight_m and url_m):
            continue

        weight = weight_m.group(1)
        url = url_m.group(1)
        unicode_range = unicode_m.group(1).strip() if unicode_m else ""

        if url not in url_to_filename:
            filename = f"inter-{weight}-{subset}.woff2"
            filepath = os.path.join(font_dir, filename)
            print(f"  Downloading {filename}...")
            data = fetch(url)
            with open(filepath, "wb") as f:
                f.write(data)
            url_to_filename[url] = filename
            print(f"    {len(data):,} bytes")
        else:
            filename = url_to_filename[url]

        local_faces.append((int(weight), subset, filename, unicode_range))

    # Generate fonts.css referencing the local files
    lines: list[str] = []
    for weight, subset, filename, unicode_range in sorted(local_faces):
        lines.append(f"/* Inter {weight} - {subset} */")
        lines.append("@font-face {")
        lines.append("  font-family: 'Inter';")
        lines.append("  font-style: normal;")
        lines.append(f"  font-weight: {weight};")
        lines.append("  font-display: swap;")
        lines.append(f"  src: url('/static/fonts/{filename}') format('woff2');")
        if unicode_range:
            lines.append(f"  unicode-range: {unicode_range};")
        lines.append("}")
        lines.append("")

    css_path = os.path.join(css_dir, "fonts.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Generated static/css/fonts.css ({len(local_faces)} @font-face rules)")


if __name__ == "__main__":
    print("=== Downloading self-hosted assets ===")
    download_tailwind()
    download_inter_fonts()
    print("=== Done ===")
