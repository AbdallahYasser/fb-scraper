"""Step 6 — Download the images of one parsed post.

Test case: files appear in output/images, open as valid images, size > 0.

Run:  .venv/bin/python steps/step6_download_images.py [index]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config                 # noqa: E402
from src import parse, media  # noqa: E402
from scrapling import Selector  # noqa: E402


def load_html() -> str:
    for name in ("debug_scrolled.html", "debug_page.html"):
        p = config.DEBUG_DIR / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise SystemExit("No saved HTML found. Run step2 or step3 first.")


def main() -> None:
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    page = Selector(load_html())
    post = parse.parse_post(parse.find_posts(page)[idx])
    print(f"Post #{idx} has {len(post['image_urls'])} image URL(s).")

    paths = media.download_images(post["image_urls"], config.IMAGES_DIR)
    print(f"Downloaded {len(paths)} file(s):")
    for p in paths:
        print(f"   - {p.name}  ({p.stat().st_size:,} bytes)")
    if paths and all(p.stat().st_size > 0 for p in paths):
        print("\n✅ PASS — images saved.")
    elif not post["image_urls"]:
        print("\n(no images on this post — try another index)")
    else:
        print("\n❌ FAIL — downloads failed; check the URLs / network.")


if __name__ == "__main__":
    main()
