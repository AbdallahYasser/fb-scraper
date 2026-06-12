"""Step 5 — Parse ONE post and print the extracted fields.

Reuses saved HTML. Lets us tune selectors in src/parse.py against real markup
without re-fetching. Pass an index to inspect a different post.

Test case: printed dict has correct text, a plausible date, a valid post URL,
and image URL(s) — verified against the post in a browser.

Run:  .venv/bin/python steps/step5_parse_one.py [index]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config            # noqa: E402
from src import parse    # noqa: E402
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
    posts = parse.find_posts(page)
    if not posts:
        raise SystemExit("No posts found — fix Step 4 first.")
    if idx >= len(posts):
        raise SystemExit(f"Only {len(posts)} posts; index {idx} out of range.")

    data = parse.parse_post(posts[idx])
    print(f"--- Post #{idx} of {len(posts)} ---")
    print("post_url :", data["post_url"])
    print("date     :", data["date"])
    print("images   :", len(data["image_urls"]))
    for u in data["image_urls"]:
        print("   -", u[:100])
    print("text     :")
    print(data["text"][:1000] or "  (empty)")


if __name__ == "__main__":
    main()
