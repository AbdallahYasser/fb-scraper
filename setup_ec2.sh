#!/usr/bin/env bash
# One-shot setup for fb-scraper on a fresh Ubuntu EC2 box.
# IMPORTANT: use Ubuntu 24.04 LTS (x86_64). The stealth browser engine
# (patchright) has NO chromium build for Ubuntu 26.04 yet.
#   ssh in, clone the repo, then:  bash setup_ec2.sh
set -euo pipefail

echo ">> [1/5] System dependencies (headless-browser libs) ..."
sudo apt-get update -y
# Best-effort: package names vary across Ubuntu releases; '|| true' so a missing
# alias doesn't abort. Camoufox bundles most of what Firefox needs.
sudo apt-get install -y git tmux curl ca-certificates xvfb fonts-liberation \
    libgtk-3-0t64 libdbus-glib-1-2 libxt6t64 libxtst6 libgl1 libpci3 \
    libasound2t64 libx11-xcb1 || \
sudo apt-get install -y git tmux curl ca-certificates xvfb fonts-liberation \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libxtst6 libgl1 libpci3 \
    libasound2 libx11-xcb1 || true

echo ">> [2/5] Swap file (safety net so the browser isn't OOM-killed) ..."
if ! sudo swapon --show | grep -q /swapfile; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
fi

echo ">> [3/5] Python 3.12 via uv (box may ship 3.14; Scrapling needs <=3.12) ..."
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12

echo ">> [4/5] Virtualenv + Python deps + stealth browser ..."
uv venv --python 3.12 .venv
# uv venvs ship without pip; install deps with uv's resolver into the venv.
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
.venv/bin/scrapling install

echo ">> [5/5] Smoke test (should print: Example Domain) ..."
.venv/bin/python steps/step1_install_check.py

cat <<'NEXT'

✅ Setup done.

Run unattended inside tmux (survives SSH drops):
    tmux new -s scrape
    .venv/bin/python index_posts.py      # Phase 1: index ALL posts
    .venv/bin/python review_index.py      # review -> pick SINCE_DATE in config.py
    .venv/bin/python fetch_archive.py      # Phase 2: resumable fetch
    # detach: Ctrl-b then d   |   reattach: tmux attach -t scrape

Pull results to your Mac (run on the Mac):
    rsync -avz -e "ssh -i fb-scraper.pem" \
      ubuntu@<PUBLIC_IP>:~/fb-scraper/output/ ./output-from-ec2/
NEXT
