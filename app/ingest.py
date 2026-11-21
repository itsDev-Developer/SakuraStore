"""Channel messages -> MongoDB posts.
A photo album (or single photo) with a caption is a post; document messages after it are its files.
Text is parsed, then translated to English; the original is kept under `orig`."""
import io

from bson import ObjectId
from PIL import Image

from . import db
from .parser import parse
from .translate import translate


async def build_meta(caption: str):
    orig = parse(caption or "")
    if not orig:
        return None
    en = {k: (v if k == "version" else await translate(v)) for k, v in orig.items()}
    return {**en, "orig": orig}


async def _store_image(msg) -> str:
    raw = await msg.download_media(bytes)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((1280, 1280))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    oid = await db.fs.upload_from_stream(f"{msg.id}.jpg", buf.getvalue(), metadata={"msg_id": msg.id})
    return str(oid)


async def _save_post(photos):
    meta = await build_meta(next((m.text for m in photos if m.text), ""))
    if not meta:
        return
    pid = photos[0].id
    old = await db.posts.find_one({"_id": pid}, {"images": 1})
    images = old["images"] if old else [await _store_image(m) for m in photos]
    await db.posts.update_one(
        {"_id": pid},
        {"$set": {**meta, "images": images, "date": photos[0].date}, "$setOnInsert": {"files": []}},
        upsert=True,
    )


async def _attach_file(m):
    post = await db.posts.find_one({"_id": {"$lt": m.id}}, {"_id": 1}, sort=[("_id", -1)])
    if not post:
        return
    f = {"id": m.id, "name": m.file.name or f"file_{m.id}", "size": m.file.size}
    await db.posts.update_one({"_id": post["_id"], "files.id": {"$ne": m.id}}, {"$push": {"files": f}})


async def ingest(messages):
    msgs = sorted((m for m in messages if m), key=lambda m: m.id)
    groups, order = {}, []
    for m in msgs:
        if m.photo:
            key = m.grouped_id or f"s{m.id}"
            if key not in groups:
                groups[key] = []
                order.append(("post", key))
            groups[key].append(m)
        elif m.document:
            order.append(("file", m))
    for kind, item in order:
        if kind == "post":
            await _save_post(groups[item])
        else:
            await _attach_file(item)


async def on_edit(m):
    meta = await build_meta(m.text or "")
    if meta:
        await db.posts.update_one({"_id": m.id}, {"$set": meta})


async def on_delete(ids):
    for pid in ids:
        p = await db.posts.find_one_and_delete({"_id": pid})
        for i in (p or {}).get("images", []):
            try:
                await db.fs.delete(ObjectId(i))
            except Exception:
                pass
    await db.posts.update_many({"files.id": {"$in": ids}}, {"$pull": {"files": {"id": {"$in": ids}}}})
