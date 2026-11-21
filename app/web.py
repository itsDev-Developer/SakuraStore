from pathlib import Path

from aiohttp import web
from bson import ObjectId

from . import bot, db
from .auth import verify_init_data

INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"
routes = web.RouteTableDef()


@routes.get("/health")
async def health(_):
    return web.Response(text="ok")


@routes.get("/")
async def index(_):
    return web.FileResponse(INDEX)


@routes.get("/api/config")
async def config(_):
    return web.json_response({"bot": bot.state["username"]})


@routes.get("/api/posts")
async def posts(req):
    limit = min(int(req.query.get("limit", 100)), 200)
    out = []
    async for p in db.posts.find({"files.0": {"$exists": True}}).sort("date", -1).limit(limit):
        p["id"] = p.pop("_id")
        p["images"] = [f"/media/{i}" for i in p["images"]]
        p["date"] = p["date"].isoformat() + "Z"
        out.append(p)
    return web.json_response(out)


@routes.get("/media/{oid}")
async def media(req):
    try:
        data = await (await db.fs.open_download_stream(ObjectId(req.match_info["oid"]))).read()
    except Exception:
        raise web.HTTPNotFound()
    return web.Response(body=data, content_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@routes.post("/api/download")
async def download(req):
    user = verify_init_data(req.headers.get("X-Init-Data", ""))
    try:
        file_id = int((await req.json())["file_id"])
    except Exception:
        raise web.HTTPBadRequest()
    try:
        await bot.send_file_to(user["id"], file_id)
    except LookupError:
        raise web.HTTPNotFound(text="file not found")
    except Exception as ex:  # user has not pressed Start yet -> bot cannot message them
        print("send failed:", repr(ex))
        raise web.HTTPConflict(text="start the bot first")
    return web.json_response({"ok": True})


def make_app():
    app = web.Application()
    app.add_routes(routes)
    return app
