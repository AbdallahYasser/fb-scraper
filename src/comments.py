"""V2: collect a post's comment thread as a Follower/Author dialog.

Strategy (validated): a post's own permalink/photo page exposes the full comment
thread logged-out. We open that page, expand "View more comments" / "View N
replies", then parse the nested comment articles into ordered dialog turns.
"""
from __future__ import annotations

import re

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
                   pause_ms: int = 2000) -> list[dict]:
    """Fetch a post's full comment thread and return dialog turns.

    Returns a list of {name, is_reply, reply_to, is_figure, text}. Empty list if
    the page can't be loaded or has no comments.
    """
    if not post_url:
        return []
    url = _story_permalink(post_url, page_url)
    try:
        page = fetch.fetch_page(url, headless=headless, max_scrolls=scrolls,
                                pause_ms=pause_ms, with_comments=True)
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not load comments for {url[:60]}: {e}")
        return []
    return parse.parse_comments(page, figure_name)
