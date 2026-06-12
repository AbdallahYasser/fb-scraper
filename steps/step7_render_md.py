"""Step 7 — Render ONE post to a Markdown study note with inline image.

This proves the core user goal on a single post: open the .md and the text reads
correctly with the photo displayed inline.

Test case: output/posts/<id>.md opens in a previewer with text + image visible.

Run:  .venv/bin/python steps/step7_render_md.py [index]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config                        # noqa: E402
from src import parse, media, render  # noqa: E402
from scrapling import Selector       # noqa: E402


def load_html() -> str:
    for name in ("debug_scrolled.html", "debug_page.html"):
        p = config.DEBUG_DIR / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise SystemExit("No saved HTML found. Run step2 or step3 first.")


def main() -> None:
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    page = Selector(load_html())
    post = parse.parse_post(parse.find_posts(page)[idx])

    img_paths = media.download_images(post["image_urls"], config.IMAGES_DIR)
    md_path = render.to_markdown(post, img_paths, config.POSTS_DIR,
                                 config.IMAGES_DIR, index=idx)
    print(f"Wrote {md_path}")
    print("\nOpen it in VS Code / Obsidian preview to confirm text + image render.")
    print("✅ = core goal proven on one post.")


if __name__ == "__main__":
    main()
