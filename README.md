# fb-scraper — personal study archive (V1)

Scrapes a public figure's Facebook **Page** into readable **Markdown notes with
inline photos**, so daily stock-market posts can be browsed/searched like a book.

**V1 scope:** post text + date + photos. Comments come in V2.

## Setup
```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/scrapling install        # downloads the stealth browser
```

## Configure
Edit `config.py` → set `PAGE_URL` to the target Page. Start with a small
`MAX_SCROLLS` while testing.

## Build/test order (each step has a pass/fail check)
```bash
.venv/bin/python steps/step1_install_check.py   # prints "Example Domain"
.venv/bin/python steps/step2_fetch_page.py      # saves debug_page.html, finds posts
.venv/bin/python steps/step3_scroll.py          # post count goes up
.venv/bin/python steps/step4_find_posts.py      # locate containers (uses saved HTML)
.venv/bin/python steps/step5_parse_one.py 0     # extract text/date/url/images of post #0
.venv/bin/python steps/step6_download_images.py 0
.venv/bin/python steps/step7_render_md.py 0     # -> output/posts/<id>.md with image
```
Steps 4–7 reuse the saved HTML, so you can tune `src/parse.py` selectors fast
without re-hitting Facebook.

## Full run
```bash
.venv/bin/python main.py            # -> output/posts/*.md + output/images/*
```

## Notes
- Built on **Scrapling** `StealthyFetcher` (stealth browser) + its adaptive parser.
- If a logged-out fetch hits a login wall, we add a session/login step using a
  **throwaway** Facebook account (never the main one; password never hardcoded).
- Personal, read-only use. Go slow / low-volume to avoid blocks.
```
