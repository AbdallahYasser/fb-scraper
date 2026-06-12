"""Step 4 — Locate post containers from saved HTML (no network needed).

Reuses debug_scrolled.html (or debug_page.html) so we can iterate on selectors
fast without re-hitting Facebook.

Test case: find_posts returns a non-empty list; count looks right.

Run:  .venv/bin/python steps/step4_find_posts.py
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
            print(f"Using {p.name}")
            return p.read_text(encoding="utf-8")
    raise SystemExit("No saved HTML found. Run step2 or step3 first.")


def main() -> None:
    page = Selector(load_html())
    posts = parse.find_posts(page)
    print(f"Found {len(posts)} post container(s).")
    if posts:
        print("\n✅ PASS — post containers located.")
    else:
        print("\n❌ FAIL — selector found nothing; inspect the HTML and tune parse.find_posts.")


if __name__ == "__main__":
    main()
