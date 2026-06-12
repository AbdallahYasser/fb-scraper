"""Phase 1 — Index ALL posts into the state DB (no comments yet).

Scrolls the whole profile, captures GraphQL to recover every post's ID, and
records id/date/preview/permalink as 'pending' in output/state.db. Safe to
re-run: it merges by post_id and never resets progress.

After this, review the index (review_index.py) to pick SINCE_DATE, then run
fetch_archive.py.

Run:  .venv/bin/python index_posts.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                              # noqa: E402
from src import fetch, parse, state, dates  # noqa: E402


def _post_id(post: dict, id_index: dict) -> str | None:
    url = post.get("post_url") or ""
    m = re.search(r"fbid=(\d+)", url) or re.search(r"story_fbid=(\d+)", url)
    if m:
        return m.group(1)
    return parse.match_post_id(id_index, post["text"]) if post["text"] else None


def main() -> None:
    print(f"Indexing {config.PAGE_URL} (up to {config.INDEX_SCROLLS} scrolls) ...")
    page = fetch.fetch_page(
        config.PAGE_URL, headless=config.HEADLESS,
        max_scrolls=config.INDEX_SCROLLS, pause_ms=config.SCROLL_PAUSE_MS,
        capture_xhr="graphql", stop_when_stable=True)

    id_index = parse.build_post_id_index(page)
    pm = re.search(r"[?&]id=(\d+)", config.PAGE_URL)
    profile_id = pm.group(1) if pm else None

    conn = state.connect(config.DB_PATH)
    articles = parse.find_posts(page)
    print(f"Found {len(articles)} post container(s); GraphQL ids: {len(id_index)}")

    added = skipped = 0
    for art in articles:
        post = parse.parse_post(art)
        if not post["text"] and not post["image_urls"]:
            continue
        pid = _post_id(post, id_index)
        if not pid or not profile_id:
            skipped += 1
            continue
        state.upsert_post(conn, {
            "post_id": pid,
            "permalink": ("https://www.facebook.com/permalink.php?"
                          f"story_fbid={pid}&id={profile_id}"),
            "date_str": post.get("date"),
            "date_iso": dates.to_iso(post.get("date")),
            "has_photo": 1 if post["image_urls"] else 0,
            "preview": (post["text"] or "")[:300],
        })
        added += 1

    st = state.stats(conn)
    print(f"\nIndexed {added} post(s) this run ({skipped} skipped, no id).")
    print(f"DB totals: {st}")
    print(f"DB: {config.DB_PATH}")
    print("Next: review_index.py to choose SINCE_DATE, then fetch_archive.py")


if __name__ == "__main__":
    main()
