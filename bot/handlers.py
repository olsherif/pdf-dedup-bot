import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import setup_logger
from bot.video_processor import VideoToPdf

logger = setup_logger(__name__)

TEMP_DIR = "/tmp/video_to_pdf_bot"
os.makedirs(TEMP_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 أرسل لي ملف فيديو للمحاضرة (mp4, avi, mov) وسأستخرج السلايدات الفريدة في PDF."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    if not video:
        # لو مش فيديو، تجاهل أو رد بخطأ
        await update.message.reply_text("الرجاء إرسال ملف فيديو.")
        return

    user = update.effective_user
    logger.info(f"Received video from {user.id}: {video.file_name} ({video.file_size} bytes)")

    # تنبيه بحجم الملف (تيليجرام بوت يقبل حتى 20MB افتراضياً)
    if video.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ حجم الفيديو أكبر من 20MB (حد البوت). حاول ضغطه.")
        return

    processing_msg = await update.message.reply_text("⏳ جاري تحميل الفيديو ومعالجته...")

    try:
        # تحميل الملف
        video_file = await video.get_file()
        video_path = os.path.join(TEMP_DIR, f"input_{user.id}.mp4")
        await video_file.download_to_drive(video_path)

        logger.info(f"Video saved to {video_path}")

        # الإعدادات
        threshold = int(os.getenv("HASH_THRESHOLD", 10))
        frame_interval = int(os.getenv("FRAME_INTERVAL", 2))
        dpi = int(os.getenv("DPI", 120))

        processor = VideoToPdf(threshold=threshold, frame_interval=frame_interval, dpi=dpi)

        # معالجة في thread
        loop = asyncio.get_running_loop()
        output_pdf = os.path.join(TEMP_DIR, f"slides_{user.id}.pdf")

        # 1. استخراج الإطارات الفريدة
        unique_images = await loop.run_in_executor(
            None,
            processor.extract_unique_frames,
            video_path
        )

        if not unique_images:
            await processing_msg.edit_text("❌ لم يتم استخراج أي سلايدات. الفيديو قد يكون قصيراً أو متشابه.")
            return

        # 2. تحويل الصور إلى PDF
        await loop.run_in_executor(
            None,
            processor.images_to_pdf,
            unique_images,
            output_pdf
        )

        await processing_msg.edit_text(f"✅ تم استخراج {len(unique_images)} سلايد فريد. جاري الإرسال...")

        # 3. إرسال PDF
        with open(output_pdf, "rb") as f:
            await update.message.reply_document(
                f,
                filename="unique_slides.pdf",
                caption=f"📎 عدد السلايدات الفريدة: {len(unique_images)}"
            )

        # تنظيف الصور المؤقتة
        for img in unique_images:
            if os.path.exists(img):
                os.remove(img)

    except Exception as e:
        logger.exception("Video processing error")
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {e}")
    finally:
        # حذف الفيديو المؤقت
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_pdf):
            os.remove(output_pdf)
