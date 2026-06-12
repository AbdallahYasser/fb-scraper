"""Extract structured post data from the Page HTML.

IMPORTANT: Facebook randomizes CSS class names, so we deliberately select on
STABLE attributes (role, aria-*, data-*) rather than classes. These selectors
are a first-pass and will be tuned in Step 5 against the real Page's HTML.

A "post" dict looks like:
    {
        "post_url":   str | None,
        "text":       str,
        "date":       str | None,   # raw text/aria value; normalized later
        "image_urls": list[str],
    }
"""
from __future__ import annotations

import re
from typing import Any


def find_posts(page: Any) -> list:
    """Return only TOP-LEVEL post containers.

    On Facebook, div[role="article"] is used for BOTH posts and comments/replies
    (comments are nested inside a post's article and carry an aria-label like
    "Comment by ..."). For V1 we want posts only, so we keep articles that are
    NOT nested inside another article.
    """
    posts = []
    for a in page.css('div[role="article"]'):
        nested = a.find_ancestor(
            lambda el: el.tag == "div" and el.attrib.get("role") == "article"
        )
        if nested is None:
            posts.append(a)
    return posts


def _in_comment(el: Any) -> bool:
    """True if `el`'s nearest role=article ancestor is a comment/reply.

    Comments are nested role=article blocks that carry an aria-label like
    "Comment by ..." / "Reply by ...", whereas the top-level post article has an
    empty aria-label. So if the closest article ancestor has a non-empty
    aria-label, this element belongs to a comment, not the post body.
    """
    anc = el.find_ancestor(
        lambda e: e.tag == "div" and e.attrib.get("role") == "article"
    )
    return anc is not None and bool(anc.attrib.get("aria-label"))


# UI toggle words injected by the "See more"/"See less" expansion — not content.
_UI_NOISE = {"see more", "see less", "عرض المزيد", "عرض أقل", "اقرأ المزيد", "المزيد"}


def _extract_text(article: Any) -> str:
    """Join the post body text, EXCLUDING any nested comment/reply text.

    FB wraps body text in dir="auto" elements, but comments live in nested
    articles inside the same container — we skip those so the note holds only
    the author's own words. We also drop the "See more"/"See less" UI toggles.
    """
    seen, out = set(), []
    for el in article.css('div[dir="auto"]'):
        if _in_comment(el):
            continue
        for node in el.css("::text"):
            t = str(node).strip()
            if t and t.lower() not in _UI_NOISE and t not in seen:
                seen.add(t)
                out.append(t)
    return "\n".join(out)


_KEEP_PARAMS = ("fbid", "story_fbid", "id", "v")  # identifiers worth keeping


def _clean_post_url(href: str) -> str:
    """Drop FB tracking params (__cft__, __tn__, ...) but KEEP the identifier
    params that make the link actually resolve (e.g. /photo/?fbid=123)."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    if not href.startswith("http"):
        href = "https://www.facebook.com" + href
    parts = urlsplit(href)
    kept = [(k, v) for k, v in parse_qsl(parts.query) if k in _KEEP_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(kept), ""))


def _extract_post_url(article: Any) -> str | None:
    """Find the permalink to the post (links containing /posts/, /photo, ...)."""
    tokens = ("/posts/", "/permalink/", "/photo", "story_fbid",
              "/reel/", "/videos/", "/story.php")
    for a in article.css("a::attr(href)"):
        href = str(a)
        if any(tok in href for tok in tokens):
            return _clean_post_url(href)
    return None


_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun",
           "jul", "aug", "sep", "oct", "nov", "dec")
# relative ("5h", "2d", "4 weeks ago"), absolute ("7 May", "July 3, 2024"),
# and the common specials.
_REL = re.compile(r"^\s*\d+\s*(h|hr|hrs|hour|hours|d|day|days|w|wk|week|weeks|"
                  r"m|min|mins|mo|month|months|y|yr|year|years)\b", re.I)


def _looks_like_date(text: str) -> bool:
    t = text.strip().lower()
    if not t or len(t) > 40:
        return False
    if t in ("yesterday", "just now") or "ago" in t:
        return True
    if _REL.match(t):
        return True
    if any(mon in t for mon in _MONTHS) and any(c.isdigit() for c in t):
        return True
    return False


def _extract_date(article: Any) -> str | None:
    """Find the post timestamp.

    FB puts the author's NAME and the DATE both in <a aria-label=...>, so we
    can't just take the first one — we pick the aria-label that looks like a date.
    """
    for sel in ('a[aria-label]::attr(aria-label)', 'a abbr::attr(aria-label)',
                'abbr::attr(title)'):
        for v in article.css(sel):
            s = str(v)
            if _looks_like_date(s):
                return s.strip()
    return None


def _extract_images(article: Any) -> list[str]:
    """Collect content image URLs, skipping tiny profile/emoji images."""
    urls = []
    for src in article.css("img::attr(src)"):
        s = str(src)
        if s.startswith("http") and "scontent" in s:  # FB CDN content images
            urls.append(s)
    # de-dupe, preserve order
    return list(dict.fromkeys(urls))


def parse_post(article: Any) -> dict:
    return {
        "post_url": _extract_post_url(article),
        "text": _extract_text(article),
        "date": _extract_date(article),
        "image_urls": _extract_images(article),
    }


# ---------------------------------------------------------------------------
# V2: comments as dialog
# ---------------------------------------------------------------------------

# Words FB injects into a comment block that aren't the actual comment text.
_COMMENT_NOISE = {
    "like", "reply", "share", "author", "follow", "see translation",
    "edit", "hide", "top fan", "most relevant", "comment", "view more comments",
    "see more", "see less", "·", "verified account",
}
_COMMENT_TIME = re.compile(
    r"^(\d+\s*[smhdwy]|\d+\s+\w+\s+ago|a\s+\w+\s+ago|an\s+\w+\s+ago|"
    r"about\s+.+\s+ago|yesterday|just now)$",
    re.I,
)


def _parse_comment_label(label: str):
    """From an aria-label, return (author_name, is_reply, reply_target)."""
    m = re.match(r"Comment by (.+?)\s+(?:\d|a |an |about |yesterday|just now)",
                 label)
    if m:
        return m.group(1).strip(), False, None
    m = re.match(r"Reply by (.+?) to (.+?)'s (?:comment|reply)", label)
    if m:
        return m.group(1).strip(), True, m.group(2).strip()
    # fallback: strip the leading verb
    name = re.sub(r"^(Comment|Reply) by ", "", label).strip()
    return name, label.startswith("Reply by"), None


def _comment_own_text(article: Any) -> str:
    """Extract a comment's own text, excluding any nested reply articles and
    the FB UI words (Like/Reply/timestamps)."""
    out, seen = [], set()
    for el in article.css('div[dir="auto"]'):
        anc = el.find_ancestor(
            lambda e: e.tag == "div" and e.attrib.get("role") == "article"
        )
        if anc is not None and anc._root is not article._root:
            continue  # belongs to a nested reply, not this comment
        for node in el.css("::text"):
            t = str(node).strip()
            if (t and t.lower() not in _COMMENT_NOISE
                    and not _COMMENT_TIME.match(t) and t not in seen):
                seen.add(t)
                out.append(t)
    return " ".join(out)


def _thread_order(turns: list[dict]) -> list[dict]:
    """Re-group turns into correct thread order: each top-level comment followed
    by its replies (incl. replies-to-replies), regardless of raw DOM order.

    Replies are flat siblings in the DOM and FB can lazy-load them out of
    position, so we rebuild threads from the "Reply by X to Y" relationship:
    a reply joins the thread of the most recent prior turn by the person it
    targets. Top-level comments keep their document order.
    """
    threads: list[dict] = []
    last_thread_of: dict[str, dict] = {}  # person name -> their current thread

    for turn in turns:
        if not turn["is_reply"]:
            thread = {"comment": turn, "replies": []}
            threads.append(thread)
            last_thread_of[turn["name"]] = thread
        else:
            target = turn.get("reply_to")
            thread = last_thread_of.get(target)
            if thread is None:
                # target unknown (scrambled / missing) -> attach to latest thread
                if not threads:
                    threads.append({"comment": turn, "replies": []})
                    last_thread_of[turn["name"]] = threads[-1]
                    continue
                thread = threads[-1]
            thread["replies"].append(turn)
            last_thread_of[turn["name"]] = thread  # repliers become reachable too

    ordered: list[dict] = []
    for thread in threads:
        ordered.append(thread["comment"])
        ordered.extend(thread["replies"])
    return ordered


def parse_comments(page: Any, figure_name: str) -> list[dict]:
    """Return ordered dialog turns from a post's permalink/photo page.

    Each turn: {name, is_reply, reply_to, is_figure, text}. The page author
    (the public figure) is detected via FB's "Author" badge OR a name match.
    Turns are re-threaded so each comment is followed by its own replies.
    """
    turns: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (author, text) -> drop double-renders
    for art in page.css('div[role="article"]'):
        label = art.attrib.get("aria-label", "")
        if not label.startswith(("Comment by", "Reply by")):
            continue
        name, is_reply, target = _parse_comment_label(label)
        text = _comment_own_text(art)
        if not text:
            continue
        # drop a leading @mention of the person being replied to (cleaner)
        if target and text.startswith(target):
            text = text[len(target):].strip()
        # FB re-renders the comment list when the sort changes (Most relevant +
        # All comments both stay in the DOM), so skip exact author+text repeats.
        key = (name.strip(), text.strip())
        if key in seen:
            continue
        seen.add(key)
        # FB tags the original poster's comments with a standalone "Author" badge
        badge = "Author" in [str(x).strip() for x in art.css("::text")]
        is_figure = badge or name.strip() == figure_name.strip()
        turns.append({
            "name": name,
            "is_reply": is_reply,
            "reply_to": target,
            "is_figure": is_figure,
            "text": text,
        })
    return _thread_order(turns)
