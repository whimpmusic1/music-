import asyncio
import importlib
import logging
import pkgutil

import plugins

from core.call import call
from core.clients import assistant, bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def load_plugins():
    for _, name, _ in pkgutil.iter_modules(plugins.__path__):
        importlib.import_module(f"plugins.{name}")


async def main():
    load_plugins()

    await bot.start()
    await assistant.start()
    await call.start()

    logging.info(
        "Music bot is live - audio + video voice-chat streaming ready."
    )

    try:
        # Keep the Railway worker alive until the platform stops/restarts it.
        await asyncio.Event().wait()
    finally:
        logging.info("Shutting down music bot...")

        try:
            await assistant.stop()
        except Exception:
            logging.exception("Failed to stop assistant cleanly")

        try:
            await bot.stop()
        except Exception:
            logging.exception("Failed to stop bot cleanly")


if __name__ == "__main__":
    asyncio.run(main())
