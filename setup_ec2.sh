#!/usr/bin/env bash
# One-shot setup for the fb-scraper on a fresh Ubuntu 24.04 (x86_64) EC2 box.
#   ssh in, clone the repo, then:  bash setup_ec2.sh
set -euo pipefail

echo ">> Installing system dependencies (Python + headless-browser libs) ..."
sudo apt-get update -y
sudo apt-get install -y \
    python3.12-venv git tmux \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libxtst6 libgl1 libpci3 \
    libasound2t64 libx11-xcb1 fonts-liberation xvfb

echo ">> Creating virtualenv + installing Python deps ..."
python3.12 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install -r requirements.txt

echo ">> Downloading the stealth browser (Camoufox) ..."
.venv/bin/scrapling install

echo ">> Smoke test (should print: Example Domain) ..."
.venv/bin/python steps/step1_install_check.py

cat <<'NEXT'

✅ Setup done.

On EC2, datacenter IPs get blocked faster — start gentle in config.py:
    COMMENT_CONCURRENCY = 2
    FETCH_DELAY = (6.0, 12.0)

Run unattended inside tmux so it survives SSH drops:
    tmux new -s scrape
    .venv/bin/python index_posts.py        # Phase 1: index all posts
    .venv/bin/python review_index.py        # pick SINCE_DATE, edit config.py
    .venv/bin/python fetch_archive.py        # Phase 2: resumable fetch
    # detach: Ctrl-b then d   |   reattach: tmux attach -t scrape

Pull results to your Mac (run on the Mac):
    rsync -avz -e "ssh -i fb-scraper.pem" \
      ubuntu@<PUBLIC_IP>:~/fb-scraper/output/ ./output-from-ec2/
NEXT
