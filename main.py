import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import start, handle_pdf
from utils.keep_alive import start_web_server
from utils.logger import setup_logger

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8000))

logger = setup_logger(__name__)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    logger.info("Starting bot and health server...")
    async with app:
        await app.initialize()
        await app.start()
        polling_task = asyncio.create_task(app.updater.start_polling())
        web_task = asyncio.create_task(start_web_server(port=PORT))

        await asyncio.gather(polling_task, web_task)

        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
