"""Render a post dict into a readable Markdown study note with inline images."""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path


def _format_date(post: dict) -> str:
    """Best available date label. Prefers the exact datetime (from the permalink
    page), then the normalized calendar date, then the raw FB label.
    e.g. 'Thursday, 11 June 2026 at 14:56'."""
    dtv = post.get("datetime")
    if dtv:
        try:
            d = _dt.datetime.fromisoformat(dtv)
            return d.strftime("%A, %d %B %Y at %H:%M")
        except ValueError:
            pass
    iso = post.get("date_iso")
    if iso:
        try:
            d = _dt.date.fromisoformat(iso)
            label = d.strftime("%A, %d %B %Y")
            raw = post.get("date")
            return f"{label} ({raw})" if raw else label
        except ValueError:
            pass
    return post.get("date") or "Unknown date"


def _slug(post: dict, fallback: str) -> str:
    url = post.get("post_url") or ""
    m = re.search(r"(\d{6,})", url)
    if m:
        return m.group(1)
    return fallback


def _render_dialog(turns: list[dict], figure_name: str,
                   images_dir: Path) -> list[str]:
    """Render comment turns as a readable Follower/Author dialog, with any
    images posted inside comments embedded inline."""
    lines = ["", "---", "", "## 💬 Discussion", ""]
    for t in turns:
        text = (t.get("text") or "").strip()
        img_paths = t.get("image_paths") or []
        if not text and not img_paths:
            continue
        if t.get("is_figure"):
            speaker = f"🎓 **{figure_name}**"
        else:
            speaker = f"👤 **{t.get('name', 'Follower')}**"
        # indent replies one level so threads read like a conversation
        prefix = "> > " if t.get("is_reply") else "> "
        lines.append(f"{prefix}{speaker}: {text}".rstrip())
        for img in img_paths:
            rel = Path("..") / images_dir.name / img.name
            lines.append(f"{prefix}![comment image]({rel.as_posix()})")
        lines.append(">")
    lines.append("")
    return lines


def to_markdown(post: dict, image_paths: list[Path], posts_dir: Path,
                images_dir: Path, index: int = 0,
                comments: list[dict] | None = None,
                figure_name: str = "") -> Path:
    """Write one .md file for a post and return its path.

    Image links are written relative to posts_dir so previewers render them inline.
    If `comments` (dialog turns) are given, they're appended as a Discussion.
    """
    posts_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug(post, fallback=f"post_{index:04d}")

    lines: list[str] = []
    lines.append(f"# Post — {_format_date(post)}\n")
    if post.get("post_url"):
        lines.append(f"[Original post]({post['post_url']})\n")
    lines.append("")
    lines.append(post.get("text", "").strip() or "_(no text)_")
    lines.append("")

    for img in image_paths:
        rel = Path("..") / images_dir.name / img.name
        lines.append(f"![image]({rel.as_posix()})")
    lines.append("")

    if comments:
        lines.extend(_render_dialog(comments, figure_name, images_dir))

    dest = posts_dir / f"{slug}.md"
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest
