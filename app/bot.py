"""Telegram bot over MTProto (Telethon + bot token). Any file size works.
Bots cannot read channel history: posts are collected live (bot must be channel admin) or via /backfill."""
from datetime import datetime

from telethon import TelegramClient, events, functions, types, utils
from telethon.errors import AuthKeyDuplicatedError
from telethon.sessions import StringSession

from . import config, db
from .ingest import ingest, on_delete, on_edit

state = {"client": None, "channel": None, "username": ""}


def webapp_row():
    return types.KeyboardButtonRow([types.KeyboardButtonWebView("🌸 Open Store", config.WEBAPP_URL)])


async def register_user(e):
    s, inp, now = await e.get_sender(), await e.get_input_sender(), datetime.utcnow()
    await db.users.update_one(
        {"_id": s.id},
        {"$set": {"username": s.username, "first_name": s.first_name,
                  "access_hash": getattr(inp, "access_hash", None), "last_seen": now},
         "$setOnInsert": {"joined": now}},
        upsert=True,
    )


async def send_file_to(user_id: int, file_msg_id: int):
    """Send an indexed channel file to a user (MTProto: any size, no upload through this server)."""
    post = await db.posts.find_one({"files.id": file_msg_id})
    if not post:
        raise LookupError("unknown file")
    c = state["client"]
    msg = await c.get_messages(state["channel"], ids=file_msg_id)
    if not msg or not msg.document:
        raise LookupError("file gone")
    u = await db.users.find_one({"_id": user_id})
    peer = types.InputPeerUser(user_id, u["access_hash"]) if u and u.get("access_hash") else user_id
    caption = f"📦 {post['title']} · v{post['version']}\n{msg.file.name or ''}".strip()
    await c.send_file(peer, msg.document, caption=caption)
    await db.downloads.insert_one({"user_id": user_id, "file_msg_id": file_msg_id, "ts": datetime.utcnow()})


async def _login():
    s = (await db.meta.find_one({"_id": "session"}) or {}).get("s", "")
    c = TelegramClient(StringSession(s), int(config.API_ID), config.API_HASH)
    try:
        await c.start(bot_token=config.BOT_TOKEN)
    except AuthKeyDuplicatedError:  # the same session ran twice at once: start clean
        c = TelegramClient(StringSession(), int(config.API_ID), config.API_HASH)
        await c.start(bot_token=config.BOT_TOKEN)
    await db.meta.update_one({"_id": "session"}, {"$set": {"s": c.session.save()}}, upsert=True)
    return c


async def _resolve_channel(c):
    try:
        ent = await c.get_entity(config.CHANNEL)
        await db.meta.update_one({"_id": "channel"}, {"$set": {"id": ent.id, "hash": ent.access_hash}}, upsert=True)
        return ent
    except Exception as ex:
        saved = await db.meta.find_one({"_id": "channel"})
        if saved:
            return types.InputPeerChannel(saved["id"], saved["hash"])
        print(f"⚠ Could not resolve channel yet ({type(ex).__name__}). Is the bot an admin of it?")
        return None


async def start_bot():
    c = state["client"] = await _login()
    me = await c.get_me()
    state["username"] = me.username
    print(f"✔ Bot logged in as @{me.username}")

    ent = await _resolve_channel(c)
    if ent is not None:
        peer = utils.get_peer_id(ent)
        print("✔ Channel found")
    elif isinstance(config.CHANNEL, int):
        peer = config.CHANNEL
        print("⚠ Private channel: post anything in it once so the bot can learn its access hash")
    else:
        raise SystemExit("❌ Channel not found. Add the bot as ADMIN, and check CHANNEL (@username or -100... id).")
    state["channel"] = ent

    async def remember_channel(e):
        if state["channel"] is None:
            inp = await e.get_input_chat()
            state["channel"] = inp
            if isinstance(inp, types.InputPeerChannel):
                await db.meta.update_one({"_id": "channel"}, {"$set": {"id": inp.channel_id, "hash": inp.access_hash}}, upsert=True)

    async def on_album(e):
        await remember_channel(e)
        await ingest(e.messages)

    async def on_new(e):
        await remember_channel(e)
        if not e.message.grouped_id:  # albums arrive through on_album
            await ingest([e.message])

    async def on_edited(e):
        await on_edit(e.message)

    async def on_deleted(e):
        await on_delete(list(e.deleted_ids))

    c.add_event_handler(on_album, events.Album(chats=peer))
    c.add_event_handler(on_new, events.NewMessage(chats=peer))
    c.add_event_handler(on_edited, events.MessageEdited(chats=peer))
    c.add_event_handler(on_deleted, events.MessageDeleted(chats=peer))

    async def start(e):
        await register_user(e)
        arg = e.pattern_match.group(1) or ""
        if arg.startswith("get_") and arg[4:].isdigit():
            try:
                await send_file_to(e.sender_id, int(arg[4:]))
            except LookupError:
                await e.respond("Sorry, that file is no longer available.")
            return
        await e.respond("🌸 **Sakura Store**\nBrowse the latest uploads in the store, or send /latest.",
                        buttons=types.ReplyInlineMarkup([webapp_row()]))

    async def latest(e):
        await register_user(e)
        lines, rows = [], []
        async for p in db.posts.find({"files.0": {"$exists": True}}).sort("date", -1).limit(5):
            desc = (p.get("description") or "").replace("\n", " ")
            lines.append(f"**{p['title']}** v{p['version']}\n{p['genre']} · {p['language']}\n{desc[:140]}{'…' if len(desc) > 140 else ''}")
            rows.append(types.KeyboardButtonRow([types.KeyboardButtonCallback(f"⬇ {p['title']}"[:40], f"get_{p['files'][0]['id']}".encode())]))
        if not lines:
            return await e.respond("No uploads yet.")
        rows.append(webapp_row())
        await e.respond("🆕 **Latest uploads**\n\n" + "\n\n".join(lines), buttons=types.ReplyInlineMarkup(rows))

    async def on_button(e):
        await register_user(e)
        try:
            await e.answer("Sending…")
            await send_file_to(e.sender_id, int(e.pattern_match.group(1)))
        except LookupError:
            await e.answer("File no longer available", alert=True)

    async def backfill(e):
        if state["channel"] is None:
            return await e.respond("Channel not resolved yet. Post something in it first.")
        a, b = int(e.pattern_match.group(1)), int(e.pattern_match.group(2))
        for s in range(a, b + 1, 100):
            await ingest(await c.get_messages(state["channel"], ids=list(range(s, min(s + 100, b + 1)))))
        await e.respond(f"Backfilled messages {a}-{b} ✅")

    private = lambda e: e.is_private
    c.add_event_handler(start, events.NewMessage(pattern=r"^/start(?:\s+(\S+))?", func=private))
    c.add_event_handler(latest, events.NewMessage(pattern=r"^/latest", func=private))
    c.add_event_handler(on_button, events.CallbackQuery(pattern=rb"get_(\d+)"))
    c.add_event_handler(backfill, events.NewMessage(pattern=r"^/backfill\s+(\d+)\s+(\d+)",
                                                    func=lambda e: e.is_private and e.sender_id in config.ADMIN_IDS))
    try:  # menu button opens the store
        await c(functions.bots.SetBotMenuButtonRequest(
            user_id=types.InputUserEmpty(), button=types.BotMenuButton(text="Store", url=config.WEBAPP_URL)))
    except Exception as ex:
        print("⚠ menu button not set:", ex)
