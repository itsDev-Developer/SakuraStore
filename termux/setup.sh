#!/data/data/com.termux/files/usr/bin/bash
# One-time setup. Run from the project folder:  bash termux/setup.sh
set -e
cd "$(dirname "$0")/.."
pkg update -y
pkg install -y python python-pillow clang cloudflared
# pure-python fallbacks: avoids C-extension build failures on Android
export MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 FROZENLIST_NO_EXTENSIONS=1 AIOHTTP_NO_EXTENSIONS=1
pip install -r requirements-termux.txt
[ -f .env ] || cp .env.example .env
echo
echo "Done. Edit .env (nano .env), then start with:  bash termux/run.sh"
