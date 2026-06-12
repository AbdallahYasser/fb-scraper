"""Step 2 — Fetch the target Page (logged-out) and save raw HTML.

Goal: confirm we can load the public Page and actually see post content without
logging in. We dump the rendered HTML to debug_page.html for inspection.

Test case:
  - debug_page.html is created and is non-trivial in size, AND
  - it contains at least one <div role="article"> (a post container), AND
  - it does NOT consist solely of a login wall.

Run:  .venv/bin/python steps/step2_fetch_page.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapling.fetchers import StealthyFetcher  # noqa: E402
import config  # noqa: E402

OUT = config.DEBUG_DIR / "debug_page.html"


def main() -> None:
    print(f"Fetching: {config.PAGE_URL}")
    page = StealthyFetcher.fetch(
        config.PAGE_URL,
        headless=config.HEADLESS,
        network_idle=True,
    )

    html = page.html_content
    OUT.write_text(html, encoding="utf-8")
    print(f"Saved {len(html):,} bytes -> {OUT}")

    articles = page.css('div[role="article"]')
    n_articles = len(articles)
    login_wall = ("log in" in html.lower() or "log into facebook" in html.lower())

    print(f"Found {n_articles} post container(s) (div[role=article]).")
    print(f"Login-related text present: {login_wall}")

    if n_articles > 0:
        print("\n✅ PASS — public post content is visible without login.")
    elif login_wall:
        print("\n⚠️  LOGIN WALL — no posts visible logged-out. "
              "We'll need the optional session/login step for this Page.")
    else:
        print("\n❌ Unexpected — no articles and no obvious login wall. "
              "Open debug_page.html to inspect.")


if __name__ == "__main__":
    main()
