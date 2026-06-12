"""Central configuration for the Facebook Page scraper.

Edit PAGE_URL to the public figure's Facebook Page, then run the step scripts.
"""
from pathlib import Path

# ---- Target ---------------------------------------------------------------
# The public Page to archive. Replace with the real Page URL.
# Use the clean Page URL, e.g. "https://www.facebook.com/SomePublicFigure"
PAGE_URL = "https://www.facebook.com/profile.php?id=61572307976850"

# ---- Scrolling / depth ----------------------------------------------------
MAX_SCROLLS = 2           # how many times to scroll the feed (more = older posts)
SCROLL_PAUSE_MS = 2500    # wait after each scroll for lazy-loaded content

# Cap how many posts to save (newest first). Set to None for no limit.
MAX_POSTS = 5

# ---- Comments (V2) --------------------------------------------------------
# When True, each post's permalink is opened to scrape the comment thread and
# render it as a Follower/Author dialog. Adds one extra fetch per post (slower).
WITH_COMMENTS = True
# The public figure's display name — used (with FB's "Author" badge) to tell
# his replies apart from followers' comments.
FIGURE_NAME = "د.مجدى الطيارى"
COMMENT_SCROLLS = 4       # scrolls on the post page to load more comments

# ---- Full-history archive (index + resumable fetch) -----------------------
INDEX_SCROLLS = 60        # max feed scrolls when indexing (stops early if stable)
BATCH_SIZE = 20           # posts per batch in the resumable fetch
# Only fetch posts on/after this date (YYYY-MM-DD). Set after reviewing the index
# to skip his older non-stock posts. None = fetch everything indexed.
SINCE_DATE = None
# DB_PATH is defined below, after the paths section (needs OUTPUT_DIR).

# Optional date cutoff: stop collecting posts older than this (YYYY-MM-DD).
# Set to None to ignore date filtering for now.
STOP_DATE = None

# ---- Browser --------------------------------------------------------------
HEADLESS = True           # True = invisible browser (faster, less CPU/RAM/heat)

# ---- Parallelism / pacing -------------------------------------------------
# How many post comment-pages to fetch at the same time. 2-3 is a good balance
# of speed vs. Facebook soft-block risk; higher = faster but riskier.
COMMENT_CONCURRENCY = 3
# Random delay (seconds) before each comment fetch, to avoid bursty traffic
# that trips Facebook's rate limits. (min, max)
FETCH_DELAY = (3.0, 7.0)

# ---- Paths ----------------------------------------------------------------
ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
POSTS_DIR = OUTPUT_DIR / "posts"
IMAGES_DIR = OUTPUT_DIR / "images"
DEBUG_DIR = ROOT  # raw HTML dumps land here during development

for _d in (OUTPUT_DIR, POSTS_DIR, IMAGES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = OUTPUT_DIR / "state.db"   # SQLite progress/state store
