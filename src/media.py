"""Download post images to the local output/images folder."""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen


def _filename_for(url: str) -> str:
    """Stable, collision-resistant filename derived from the URL."""
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    # try to keep a sensible extension
    ext = ".jpg"
    for cand in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if cand in url.lower():
            ext = cand
            break
    return f"{h}{ext}"


def download_images(image_urls: list[str], images_dir: Path) -> list[Path]:
    """Download each URL into images_dir. Returns local paths of saved files."""
    images_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for url in image_urls:
        dest = images_dir / _filename_for(url)
        if dest.exists() and dest.stat().st_size > 0:
            saved.append(dest)
            continue
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
            if data:
                dest.write_bytes(data)
                saved.append(dest)
        except Exception as e:  # noqa: BLE001 — best-effort, keep going
            print(f"  ! failed to download {url[:80]}... : {e}")
    return saved
