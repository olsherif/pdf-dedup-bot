import os
import asyncio
from pyrogram import Client, filters
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn

# بياناتك الرسمية اللي بعتها
BOT_TOKEN = "7666201765:AAGUzeDLniXy5jBbJ0tvMWrNJJx4jRaKuRA"
API_ID = 29250880
API_HASH = "efd75c5c849f429cbd0651d74a94da13"
ADMIN_CHAT_ID = 29250880  # حسابك عشان أنت بس اللي تتحكم فيه

PORT = int(os.environ.get("PORT", 8000))
app = FastAPI()

# تشغيل البوت عبر مكتبة Pyrogram لتخطي حد الـ 20 ميجا
bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
file_db = {}

@bot.on_message(filters.private & (filters.video | filters.document))
async def handle_video(client, message):
    # حماية البوت عشان محدش غريب يستهلك سيرفرك المجاني
    if message.chat.id != ADMIN_CHAT_ID:
        await message.reply_text("عذراً، هذا البوت خاص بصاحبه فقط.")
        return

    file_id = message.id
    file_db[file_id] = message
    
    # اسم الدومين المؤقت من Koyeb سيتعرف عليه تلقائياً
    domain = os.environ.get("KOYEB_APP_NAME", "localhost")
    public_link = f"https://{domain}.koyeb.app/stream/{file_id}"
    
    await message.reply_text(
        f"✅ **تمت العملية بنجاح وبدون قيود الـ 20 ميجا!**\n\n"
        f"🔗 **رابط الويب العام للفيديو:**\n{public_link}\n\n"
        f"ℹ️ ابعته لزمايلك وهيفتح معاهم أونلاين أو تحميل مباشر."
    )

async def media_streamer(message):
    async for chunk in bot.download_media(message, block=True):
        yield chunk

@app.get("/stream/{file_id}")
async def stream_file(file_id: int):
    if file_id not in file_db:
        return {"error": "الملف غير موجود أو انتهت الجلسة"}
    
    message = file_db[file_id]
    media = message.video or message.document
    
    return StreamingResponse(
        media_streamer(message),
        media_type=media.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={media.file_name}",
            "Content-Length": str(media.file_size)
        }
    )

async def start_services():
    await bot.start()
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start_services())
