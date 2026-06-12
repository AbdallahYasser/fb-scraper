"""Throwaway inspection: understand the comment/reply markup on real posts.

Fetches the profile, then for the first few posts prints each nested article
(comment/reply): its aria-label, whether an "Author" badge is present, and a
snippet of text. Helps design the V2 comment parser.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config            # noqa: E402
from src import fetch, parse  # noqa: E402

HTML_OUT = config.DEBUG_DIR / "debug_comments.html"


def main() -> None:
    page = fetch.fetch_page(config.PAGE_URL, headless=config.HEADLESS,
                            max_scrolls=config.MAX_SCROLLS,
                            pause_ms=config.SCROLL_PAUSE_MS,
                            with_comments=True)
    HTML_OUT.write_text(page.html_content, encoding="utf-8")
    print(f"Saved HTML -> {HTML_OUT}\n")

    posts = parse.find_posts(page)
    print(f"top-level posts: {len(posts)}\n")

    shown = 0
    for pi, post in enumerate(posts):
        body = parse.parse_post(post)
        if not body["text"]:
            continue
        # comments/replies = nested articles whose aria-label starts Comment/Reply
        comments = [c for c in post.css('div[role="article"]')
                    if c.attrib.get("aria-label", "").startswith(("Comment by", "Reply by"))]
        if not comments:
            continue
        shown += 1
        print("=" * 60)
        print(f"POST #{pi}  date={body['date']}  comments={len(comments)}")
        print(f"  body: {body['text'][:45].strip()}")
        for ci, c in enumerate(comments):
            label = c.attrib.get("aria-label", "")
            is_reply = label.startswith("Reply by")
            # "Author" badge = a standalone text node "Author" inside the comment
            texts = [str(x).strip() for x in c.css("::text")]
            has_author_badge = "Author" in texts
            print(f"   [{ci}] {'REPLY' if is_reply else 'COMMENT'} "
                  f"author_badge={has_author_badge}  label={label[:48]!r}")
        if shown >= 4:
            break


if __name__ == "__main__":
    main()
