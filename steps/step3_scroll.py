"""Step 3 — Scroll the feed to lazy-load more posts.

Test case: the number of post containers after scrolling should be GREATER than
without scrolling (proves lazy-loading works).

Run:  .venv/bin/python steps/step3_scroll.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config            # noqa: E402
from src import fetch, parse  # noqa: E402

OUT = config.DEBUG_DIR / "debug_scrolled.html"


def main() -> None:
    print(f"Fetching with {config.MAX_SCROLLS} scrolls: {config.PAGE_URL}")
    page = fetch.fetch_page(
        config.PAGE_URL,
        headless=config.HEADLESS,
        max_scrolls=config.MAX_SCROLLS,
        pause_ms=config.SCROLL_PAUSE_MS,
    )
    html = page.html_content
    OUT.write_text(html, encoding="utf-8")
    n = len(parse.find_posts(page))
    print(f"Saved {len(html):,} bytes -> {OUT}")
    print(f"Post containers after scrolling: {n}")
    print("\nCompare against Step 2's count. Higher = ✅ scrolling works.")


if __name__ == "__main__":
    main()
