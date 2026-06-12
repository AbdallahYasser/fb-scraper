"""Full run: scroll the feed, parse posts, download images, fetch each post's
comment thread (in parallel), and render one Markdown study note per post.

Run:  .venv/bin/python main.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                         # noqa: E402
from src import fetch, parse, media, render, comments  # noqa: E402


def main() -> None:
    # 1) Open the feed once and pull post text/date/photo/link from it.
    print(f"Fetching {config.PAGE_URL} (scrolls={config.MAX_SCROLLS}, "
          f"headless={config.HEADLESS}) ...")
    page = fetch.fetch_page(
        config.PAGE_URL,
        headless=config.HEADLESS,
        max_scrolls=config.MAX_SCROLLS,
        pause_ms=config.SCROLL_PAUSE_MS,
        capture_xhr="graphql",   # capture GraphQL to recover post IDs
    )
    articles = parse.find_posts(page)
    print(f"Found {len(articles)} post container(s).")

    # Build a text -> post_id index from the feed's GraphQL so text-only posts
    # (no photo link) can still get a real permalink + comments.
    id_index = parse.build_post_id_index(page)
    profile_id = re.search(r"[?&]id=(\d+)", config.PAGE_URL)
    profile_id = profile_id.group(1) if profile_id else None

    # 2) Select the posts to keep (dedupe by URL, skip empty shells, cap count).
    selected: list[tuple[int, dict]] = []
    seen_urls: set[str] = set()
    for i, article in enumerate(articles):
        post = parse.parse_post(article)

        # If the post has no permalink (text-only posts), recover its ID from the
        # GraphQL index and build the canonical story permalink.
        if not post.get("post_url") and profile_id and post["text"]:
            pid = parse.match_post_id(id_index, post["text"])
            if pid:
                post["post_url"] = ("https://www.facebook.com/permalink.php?"
                                    f"story_fbid={pid}&id={profile_id}")

        url = post.get("post_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        if not post["text"] and not post["image_urls"]:
            continue
        selected.append((i, post))
        if config.MAX_POSTS is not None and len(selected) >= config.MAX_POSTS:
            break
    print(f"Selected {len(selected)} post(s).")

    # 3) Download each post's images (quick, sequential).
    for _, post in selected:
        post["_img_paths"] = media.download_images(post["image_urls"],
                                                   config.IMAGES_DIR)

    # 4) Fetch all comment threads IN PARALLEL (the slow part).
    dialogs: dict[int, list] = {}
    if config.WITH_COMMENTS:
        jobs = [(i, post["post_url"]) for i, post in selected if post.get("post_url")]
        print(f"Fetching comments for {len(jobs)} post(s), "
              f"{config.COMMENT_CONCURRENCY} at a time ...")
        dialogs = comments.collect_dialogs_parallel(
            jobs, config.FIGURE_NAME, config.PAGE_URL,
            headless=config.HEADLESS, scrolls=config.COMMENT_SCROLLS,
            pause_ms=config.SCROLL_PAUSE_MS,
            concurrency=config.COMMENT_CONCURRENCY, delay=config.FETCH_DELAY)

    # 5) Render one Markdown note per post.
    written = 0
    for i, post in selected:
        dialog = dialogs.get(i, [])
        md = render.to_markdown(post, post["_img_paths"], config.POSTS_DIR,
                                config.IMAGES_DIR, index=i,
                                comments=dialog, figure_name=config.FIGURE_NAME)
        written += 1
        figs = sum(t["is_figure"] for t in dialog)
        print(f"  [{written}] {md.name}  ({len(post['_img_paths'])} img, "
              f"{len(dialog)} comments, {figs} by {config.FIGURE_NAME})")

    print(f"\nDone. Wrote {written} note(s) to {config.POSTS_DIR}")


if __name__ == "__main__":
    main()
