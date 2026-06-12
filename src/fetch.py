"""Fetching + scrolling helpers built on Scrapling's StealthyFetcher.

Kept deliberately small: one function to fetch a Page with optional scrolling.
The scrolling is done via a `page_action` hook that Scrapling passes the live
Playwright page to, so we can scroll/click before the HTML is captured.
"""
from __future__ import annotations

import re

from scrapling.fetchers import StealthyFetcher


# "See more" button label across the locales FB may serve.
_SEE_MORE_LABELS = ("See more", "See More", "عرض المزيد", "اقرأ المزيد", "المزيد")


def _expand_truncated(page, max_clicks: int = 60) -> None:
    """Click every "See more" button so full (not truncated) post text loads.

    FB renders these as role=button divs. Clicking one replaces its text, so we
    repeatedly click the first remaining match until none are left.
    """
    for label in _SEE_MORE_LABELS:
        clicks = 0
        while clicks < max_clicks:
            try:
                loc = page.get_by_text(label, exact=True)
                if loc.count() == 0:
                    break
                loc.first.click(timeout=800)
                page.wait_for_timeout(200)
            except Exception:  # noqa: BLE001 — best effort, skip stuck buttons
                break
            clicks += 1


# Comment/reply expander buttons we DO want to click...
_EXPAND_COMMENTS = re.compile(
    r"(view\s+\d+\s+repl|view\s+all\s+\d+\s+repl|\d+\s+repl(y|ies)|"
    r"view\s+more\s+comment|view\s+previous\s+comment|view\s+\d+\s+more\s+comment|"
    r"عرض المزيد من التعليقات|عرض .* رد|الردود)",
    re.I,
)
# ...but NOT these bare action buttons (writing a reply/comment, liking, etc.)
_SKIP_BUTTONS = {"reply", "comment", "like", "share", "send", "رد", "تعليق", "إعجاب"}


# The comment-sort dropdown trigger labels, and the option we want.
_SORT_TRIGGERS = ("Most relevant", "All comments", "Newest",
                  "الأكثر صلة", "الأحدث", "كل التعليقات")
_ALL_COMMENTS = ("All comments", "كل التعليقات")


def _select_all_comments(page) -> None:
    """Switch the comment sort from "Most relevant" to "All comments" so the
    full set (newest + everything, incl. potential spam) loads before we expand.
    """
    try:
        # open the sort dropdown (whatever it currently reads)
        trigger = None
        for label in _SORT_TRIGGERS:
            loc = page.get_by_text(label, exact=True)
            if loc.count() > 0:
                trigger = loc.first
                break
        if trigger is None:
            return
        trigger.scroll_into_view_if_needed(timeout=1000)
        trigger.click(timeout=1200)
        page.wait_for_timeout(900)
        # pick "All comments" from the opened menu
        for label in _ALL_COMMENTS:
            opt = page.get_by_text(label, exact=True)
            if opt.count() > 0:
                opt.last.click(timeout=1200)  # .last = the menu item, not trigger
                page.wait_for_timeout(1800)    # let comments reload
                return
    except Exception:  # noqa: BLE001 — best effort; fall back to default sort
        pass


def _expand_comments(page, rounds: int = 8) -> None:
    """Click "View more comments" / "View N replies" links to surface threads.

    FB renders these as clickable spans (not always role=button), so we match by
    TEXT. Re-queries each round because expanding mutates the DOM. We scroll each
    match into view before clicking; bare action buttons are excluded by regex.
    """
    for _ in range(rounds):
        clicked = 0
        try:
            loc = page.get_by_text(_EXPAND_COMMENTS)
            n = loc.count()
        except Exception:  # noqa: BLE001
            return
        for i in range(n):
            try:
                el = loc.nth(i)
                txt = (el.inner_text(timeout=300) or "").strip()
                if not txt or txt.lower() in _SKIP_BUTTONS:
                    continue
                el.scroll_into_view_if_needed(timeout=600)
                el.click(timeout=800)
                page.wait_for_timeout(350)
                clicked += 1
            except Exception:  # noqa: BLE001
                continue
        if clicked == 0:
            break


def make_scroller(max_scrolls: int, pause_ms: int, with_comments: bool = False):
    """page_action that scrolls, expands truncated posts, and (optionally)
    expands comment threads."""

    def _action(page):
        for _ in range(max_scrolls):
            page.keyboard.press("End")
            page.wait_for_timeout(pause_ms)
        if with_comments:
            _select_all_comments(page)  # switch sort to "All comments" first
            _expand_comments(page)
        _expand_truncated(page)  # also expands long comments now that they're open
        page.wait_for_timeout(500)
        return page

    return _action


def fetch_page(url: str, *, headless: bool = False, max_scrolls: int = 0,
               pause_ms: int = 2500, with_comments: bool = False,
               retries: int = 2):
    """Fetch `url` with the stealth browser, optionally scrolling first.

    Retries on transient navigation timeouts (FB can be slow). Returns the
    Scrapling page/Adaptor object (use .html_content, .css(), etc).
    """
    if max_scrolls > 0 or with_comments:
        page_action = make_scroller(max(max_scrolls, 1), pause_ms, with_comments)
    else:
        page_action = None

    last_err = None
    for attempt in range(1, retries + 2):
        try:
            return StealthyFetcher.fetch(
                url,
                headless=headless,
                network_idle=True,
                timeout=60000,            # 60s nav timeout (default 30s is tight for FB)
                page_action=page_action,
            )
        except Exception as e:  # noqa: BLE001 — retry transient timeouts
            last_err = e
            if attempt <= retries:
                print(f"  ! fetch failed (attempt {attempt}): {str(e)[:80]} — retrying")
    raise last_err
