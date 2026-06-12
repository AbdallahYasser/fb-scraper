"""Review the indexed posts so you can choose SINCE_DATE (where stock content
starts). Lists posts newest->oldest with date + preview.

Run:  .venv/bin/python review_index.py          (all)
      .venv/bin/python review_index.py 2025      (only rows whose date contains 2025)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config            # noqa: E402
from src import state    # noqa: E402


def main() -> None:
    needle = sys.argv[1] if len(sys.argv) > 1 else None
    conn = state.connect(config.DB_PATH)
    rows = conn.execute(
        "SELECT * FROM posts ORDER BY date_iso DESC NULLS LAST").fetchall()
    print(f"{state.stats(conn)}\n")
    for r in rows:
        line = (f"{(r['date_iso'] or '?'):10}  {(r['date_str'] or ''):8.8}  "
                f"[{r['status'][:4]}] {'📷' if r['has_photo'] else '  '} "
                f"{(r['preview'] or '').splitlines()[0][:60]}")
        if not needle or needle in line:
            print(line)


if __name__ == "__main__":
    main()
