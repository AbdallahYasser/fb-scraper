"""Step 1 — Environment & install sanity check.

Goal: prove Scrapling + its stealth browser actually work in this venv before we
touch Facebook at all.

Test case: this should print the page title  ->  Example Domain
Run:  .venv/bin/python steps/step1_install_check.py
"""
from scrapling.fetchers import StealthyFetcher


def main() -> None:
    print("Fetching https://example.com with StealthyFetcher ...")
    page = StealthyFetcher.fetch("https://example.com", headless=True)

    titles = page.css("title::text")
    title = str(titles[0]) if titles else None
    print("Status:", getattr(page, "status", "n/a"))
    print("Page title:", title)

    if title and "Example Domain" in title:
        print("\n✅ PASS — Scrapling + stealth browser are working.")
    else:
        print("\n❌ FAIL — got an unexpected title; investigate before continuing.")


if __name__ == "__main__":
    main()
