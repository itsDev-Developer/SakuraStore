#!/data/data/com.termux/files/usr/bin/bash
# Starts a free Cloudflare quick-tunnel (public HTTPS URL) and the bot.
cd "$(dirname "$0")/.."
termux-wake-lock 2>/dev/null || true
set -a; . ./.env; set +a
export PORT="${PORT:-8080}"
if [ -z "$WEBAPP_URL" ] || [ "$WEBAPP_URL" = "auto" ]; then
  cloudflared tunnel --url "http://localhost:$PORT" > "$TMPDIR/cf.log" 2>&1 &
  for i in $(seq 1 40); do
    URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TMPDIR/cf.log" | head -1)
    [ -n "$URL" ] && break
    sleep 1
  done
  [ -z "$URL" ] && { echo "Tunnel failed, see $TMPDIR/cf.log"; exit 1; }
  export WEBAPP_URL="$URL"
fi
echo "Store URL: $WEBAPP_URL"
exec python -m app
