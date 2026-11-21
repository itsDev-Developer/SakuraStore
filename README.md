# Sakura Store: Telegram channel -> anime app store Mini App

Telegram bot (MTProto/Telethon, bot token) + aiohttp web app + MongoDB.
Posts are read from your channel, Russian text is translated to English, files of any size are sent by the bot.

## 0. Common setup (all methods)
1. @BotFather -> `/newbot` -> copy the token.
2. https://my.telegram.org -> API development tools -> `API_ID`, `API_HASH`.
3. Add the bot to your channel as **admin** (it only receives posts when admin). Public @username is easiest.
4. MongoDB: local/Docker Mongo, or free **MongoDB Atlas** (needed for Termux/Render/Koyeb; allow `0.0.0.0/0` in Network Access).
5. `cp .env.example .env` and fill it in.

## 1. Plain Python (PC / VPS)
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# needs a public HTTPS URL in WEBAPP_URL (e.g. `cloudflared tunnel --url http://localhost:8000`)
python -m app
```

## 2. Docker (VPS with a domain)
Set `DOMAIN`, point its DNS to the server, `WEBAPP_URL=https://<DOMAIN>` in `.env`, then:
```
docker compose up -d --build
```
Includes MongoDB and Caddy (automatic HTTPS). Without compose: `docker build -t sakura . && docker run --env-file .env -p 8000:8000 sakura`.

## 3. Termux (Android)
```
pkg install git && git clone <your repo> sakura-store   # or unzip it
cd sakura-store && bash termux/setup.sh
nano .env          # API_ID, API_HASH, BOT_TOKEN, CHANNEL, MONGO_URI (Atlas); leave WEBAPP_URL=auto
bash termux/run.sh
```
`run.sh` opens a free Cloudflare tunnel and sets the store URL automatically (it changes each run, the bot updates its menu button itself). Keep Termux in the background with the wake-lock notification on.

## 4. Render
Push the project to GitHub, then Render -> New -> **Blueprint** (uses `render.yaml`), fill the secrets (`MONGO_URI` = Atlas string). `WEBAPP_URL` is detected automatically.
Free web services sleep after ~15 min without HTTP traffic, which stops the bot: create a free UptimeRobot/cron-job.org monitor for `https://<app>.onrender.com/health` every 5 minutes.

## 5. Koyeb
Push to GitHub, Koyeb -> Create Service -> GitHub -> builder **Dockerfile**, port **8000** (HTTP), health check path `/health`, add the env vars from `.env.example` (`WEBAPP_URL=auto`: Koyeb's domain is detected). Keep **one** instance only.
Free instances can scale to zero when idle: ping `/health` every 5 minutes as above.
CLI: `koyeb app init sakura-store --git github.com/<you>/<repo> --git-branch main --git-builder docker --ports 8000:http --routes /:8000 --env API_ID=... --env API_HASH=... --env BOT_TOKEN=... --env CHANNEL=@TestCh --env MONGO_URI=... --env WEBAPP_URL=auto`

## How it works
Photo album + caption (Title / Description / Genre / Language / Censorship, English or Russian labels) = a post. Documents sent after it = its files (APK etc).
Russian (any non-English) text is translated to English; the original is kept in MongoDB under `orig`. Disable with `TRANSLATE_TO=`.
Download button -> signed request -> the bot sends the file to the user's chat (works for 90 MB+). If they never pressed Start, the app opens the bot with a deep link.
Bot commands: `/start`, `/latest`, `/backfill <from_id> <to_id>` (admins; old posts, because bots cannot read history).
MongoDB collections: `posts`, `users`, `downloads`, `meta` (bot session), `images.*` (GridFS).

## Troubleshooting
| Message | Fix |
|---|---|
| Missing settings: ... | fill those keys in `.env` / host env vars |
| Cannot connect to MongoDB | wrong `MONGO_URI`, or Atlas IP allow-list |
| Channel not found | add the bot as admin; use `@username` or `-100...` id and post once |
| WEBAPP_URL must be https | use the tunnel / host domain |
| AuthKeyDuplicated | two copies of the bot are running; keep one |
| Store shows demo apps | `/api/posts` is empty: post an album + file in the channel (or `/backfill`) |
