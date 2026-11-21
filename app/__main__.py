import asyncio

from aiohttp import web

from . import bot, config, db
from .web import make_app


async def main():
    config.check()
    await db.init()
    print("✔ MongoDB connected")
    runner = web.AppRunner(make_app())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.PORT).start()  # bind early so hosts see the port
    print(f"✔ Web server on :{config.PORT}  ->  {config.WEBAPP_URL}")
    await bot.start_bot()
    print("✔ Ready. Post in the channel, then open the bot and send /start")
    await bot.state["client"].run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
