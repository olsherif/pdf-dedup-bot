import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import start, handle_video
from utils.keep_alive import start_web_server
from utils.logger import setup_logger

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8000))

logger = setup_logger(__name__)

async def main():
    start_web_server()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # استقبال الفيديوهات فقط
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    logger.info("Bot started...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
