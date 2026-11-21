"""MongoDB. The client is created inside the running event loop (avoids 'attached to a different loop')."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from . import config

client = database = posts = users = downloads = meta = fs = None


async def init():
    global client, database, posts, users, downloads, meta, fs
    client = AsyncIOMotorClient(config.MONGO_URI, serverSelectionTimeoutMS=8000)
    try:
        await client.admin.command("ping")
    except Exception as ex:
        raise SystemExit(
            f"❌ Cannot connect to MongoDB ({type(ex).__name__}). Check MONGO_URI; "
            "on Atlas allow your server's IP (or 0.0.0.0/0) under Network Access."
        )
    database = client[config.MONGO_DB]
    posts, users, downloads, meta = database.posts, database.users, database.downloads, database.meta
    fs = AsyncIOMotorGridFSBucket(database, bucket_name="images")
    await posts.create_index([("date", -1)])
    await posts.create_index("files.id")
    await downloads.create_index([("user_id", 1), ("ts", -1)])
