"""Step 8 — Full V1 run: scroll the Page, parse all posts, download images,
render each to a Markdown study note. Dedupes by post URL, optional date cutoff.

Run:  .venv/bin/python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                         # noqa: E402
from src import fetch, parse, media, render, comments  # noqa: E402


def main() -> None:
    print(f"Fetching {config.PAGE_URL} (scrolls={config.MAX_SCROLLS}) ...")
    page = fetch.fetch_page(
        config.PAGE_URL,
        headless=config.HEADLESS,
        max_scrolls=config.MAX_SCROLLS,
        pause_ms=config.SCROLL_PAUSE_MS,
    )

    posts = parse.find_posts(page)
    print(f"Found {len(posts)} post container(s).")

    seen_urls: set[str] = set()
    written = 0
    for i, article in enumerate(posts):
        post = parse.parse_post(article)

        url = post.get("post_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        if not post["text"] and not post["image_urls"]:
            continue  # skip empty shells

        img_paths = media.download_images(post["image_urls"], config.IMAGES_DIR)

        dialog = []
        if config.WITH_COMMENTS and post.get("post_url"):
            dialog = comments.collect_dialog(
                post["post_url"], config.FIGURE_NAME, config.PAGE_URL,
                headless=config.HEADLESS, scrolls=config.COMMENT_SCROLLS)

        md = render.to_markdown(post, img_paths, config.POSTS_DIR,
                                config.IMAGES_DIR, index=i,
                                comments=dialog, figure_name=config.FIGURE_NAME)
        written += 1
        figs = sum(t["is_figure"] for t in dialog)
        print(f"  [{written}] {md.name}  ({len(img_paths)} img, "
              f"{len(dialog)} comments, {figs} by {config.FIGURE_NAME})")

        if config.MAX_POSTS is not None and written >= config.MAX_POSTS:
            print(f"Reached MAX_POSTS={config.MAX_POSTS}; stopping.")
            break

    print(f"\nDone. Wrote {written} note(s) to {config.POSTS_DIR}")


if __name__ == "__main__":
    main()
