"""V2: collect a post's comment thread as a Follower/Author dialog.

Strategy (validated): a post's own permalink/photo page exposes the full comment
thread logged-out. We open that page, expand "View more comments" / "View N
replies", then parse the nested comment articles into ordered dialog turns.
"""
from __future__ import annotations

import concurrent.futures as cf
import random
import re
import time

from . import fetch, parse


def _story_permalink(post_url: str, page_url: str) -> str:
    """Build the post's STORY permalink (full comment thread).

    The /photo/?fbid= URL only shows a limited comment subset in the photo
    viewer, whereas permalink.php?story_fbid=<fbid>&id=<profile_id> shows the
    whole thread. Falls back to post_url if the ids can't be found.
    """
    mid = re.search(r"[?&]id=(\d+)", page_url or "")
    mfb = re.search(r"fbid=(\d+)", post_url or "") or \
        re.search(r"story_fbid=(\d+)", post_url or "")
    if mid and mfb:
        return ("https://www.facebook.com/permalink.php?"
                f"story_fbid={mfb.group(1)}&id={mid.group(1)}")
    return post_url


def collect_dialog(post_url: str, figure_name: str, page_url: str = "", *,
                   headless: bool = False, scrolls: int = 3,
                   pause_ms: int = 2000, delay: tuple | None = None) -> list[dict]:
    """Fetch a post's full comment thread and return dialog turns.

    Returns a list of {name, is_reply, reply_to, is_figure, text}. Empty list if
    the page can't be loaded or has no comments. `delay` = (min, max) seconds to
    sleep first, to avoid bursty traffic when many run in parallel.
    """
    if not post_url:
        return []
    if delay:
        time.sleep(random.uniform(*delay))
    url = _story_permalink(post_url, page_url)
    try:
        page = fetch.fetch_page(url, headless=headless, max_scrolls=scrolls,
                                pause_ms=pause_ms, with_comments=True)
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not load comments for {url[:60]}: {e}")
        return []
    return parse.parse_comments(page, figure_name)


def fetch_post_and_comments(permalink: str, figure_name: str, *,
                            headless: bool = True, scrolls: int = 4,
                            pause_ms: int = 2000, delay: tuple | None = None):
    """Open a post's permalink ONCE and return (post_dict, comment_turns).

    Used by the resumable archive fetcher — the permalink page carries both the
    full post content and its comment thread.
    """
    if delay:
        time.sleep(random.uniform(*delay))
    try:
        page = fetch.fetch_page(permalink, headless=headless, max_scrolls=scrolls,
                                pause_ms=pause_ms, with_comments=True)
    except Exception as e:  # noqa: BLE001
        print(f"  ! fetch failed {permalink[:55]}: {e}")
        return None, []
    tops = parse.find_posts(page)
    post = parse.parse_post(tops[0]) if tops else {}
    post["datetime"] = parse.extract_post_time(page)  # exact date+time
    turns = parse.parse_comments(page, figure_name)
    return post, turns


def fetch_archive_batch(jobs: list[tuple], figure_name: str, *,
                        headless: bool = True, scrolls: int = 4,
                        pause_ms: int = 2000, concurrency: int = 3,
                        delay: tuple | None = None) -> dict:
    """Fetch a batch of posts (post + comments) concurrently.

    `jobs` = list of (post_id, permalink). Returns {post_id: (post, turns)}.
    """
    results: dict = {}

    def _work(pid, permalink):
        return pid, fetch_post_and_comments(
            permalink, figure_name, headless=headless, scrolls=scrolls,
            pause_ms=pause_ms, delay=delay)

    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(_work, pid, url) for pid, url in jobs if url]
        for fut in cf.as_completed(futures):
            try:
                pid, payload = fut.result()
                results[pid] = payload
            except Exception as e:  # noqa: BLE001
                print(f"  ! archive job failed: {e}")
    return results


def collect_dialogs_parallel(jobs: list[tuple], figure_name: str, page_url: str,
                             *, headless: bool = True, scrolls: int = 3,
                             pause_ms: int = 2000, concurrency: int = 3,
                             delay: tuple | None = None) -> dict:
    """Fetch many posts' comment threads concurrently.

    `jobs` is a list of (key, post_url). Each runs collect_dialog in its own
    browser via a thread pool (reuses all the sync fetch/expand logic). Returns
    {key: dialog_turns}. A staggered random `delay` spreads out the requests.
    """
    results: dict = {}

    def _work(key, post_url):
        return key, collect_dialog(
            post_url, figure_name, page_url, headless=headless,
            scrolls=scrolls, pause_ms=pause_ms, delay=delay)

    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(_work, key, url) for key, url in jobs if url]
        for fut in cf.as_completed(futures):
            try:
                key, dialog = fut.result()
                results[key] = dialog
            except Exception as e:  # noqa: BLE001
                print(f"  ! comment job failed: {e}")
    return results
