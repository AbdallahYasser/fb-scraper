"""Phase 2 — Resumable archive fetch.

Reads 'pending' (and previously 'failed') posts from the state DB, fetches each
post + its comments in parallel batches, writes a Markdown note, and marks the
post 'done'. Safe to stop (Ctrl-C) and re-run any time — finished posts are
skipped, failures are retried. Honors config.SINCE_DATE.

Run:  .venv/bin/python fetch_archive.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                                  # noqa: E402
from src import state, comments, media, render  # noqa: E402


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main() -> None:
    conn = state.connect(config.DB_PATH)
    pending = state.get_pending(conn, since_iso=config.SINCE_DATE,
                                newest_first=True)
    print(f"State: {state.stats(conn)}")
    print(f"To fetch: {len(pending)} post(s)"
          + (f" since {config.SINCE_DATE}" if config.SINCE_DATE else "")
          + f", {config.BATCH_SIZE}/batch, {config.COMMENT_CONCURRENCY} parallel\n")

    done = 0
    for batch in _chunks(pending, config.BATCH_SIZE):
        jobs = [(r["post_id"], r["permalink"]) for r in batch]
        results = comments.fetch_archive_batch(
            jobs, config.FIGURE_NAME, headless=config.HEADLESS,
            scrolls=config.COMMENT_SCROLLS, pause_ms=config.SCROLL_PAUSE_MS,
            concurrency=config.COMMENT_CONCURRENCY, delay=config.FETCH_DELAY)

        for r in batch:
            pid = r["post_id"]
            post, turns = results.get(pid, (None, []))
            if post is None:
                state.mark(conn, pid, "failed")
                print(f"  FAILED {pid}")
                continue
            # Use the canonical permalink from the DB (numeric story_fbid =
            # post_id) so the filename/link are stable and correct.
            post["post_url"] = r["permalink"]
            if not post.get("text"):
                post["text"] = r["preview"] or ""
            if not post.get("date"):
                post["date"] = r["date_str"]

            imgs = media.download_images(post.get("image_urls", []),
                                         config.IMAGES_DIR)
            for t in turns:
                t["image_paths"] = media.download_images(
                    t.get("image_urls", []), config.IMAGES_DIR)

            md = render.to_markdown(post, imgs, config.POSTS_DIR,
                                    config.IMAGES_DIR, comments=turns,
                                    figure_name=config.FIGURE_NAME)
            state.mark(conn, pid, "done", note_path=str(md),
                       n_comments=len(turns))
            done += 1
            print(f"  [{done}] {md.name}  ({len(turns)} comments)")

        print(f"  -- batch done; {state.stats(conn)}")

    print(f"\nFinished. {done} note(s) written this run. {state.stats(conn)}")


if __name__ == "__main__":
    main()
