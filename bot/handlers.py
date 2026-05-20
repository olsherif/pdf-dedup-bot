import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import setup_logger
from bot.pdf_processor import PdfDeduplicator

logger = setup_logger(__name__)

# مجلد مؤقت - Koyeb هيحذف أي حاجة مش في الـ Volume، فخلينا في المسار العادي
TEMP_DIR = "/tmp/pdf_dedup_bot"
os.makedirs(TEMP_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 أرسل لي ملف PDF (سكرينشوتات محاضرة مثلاً) "
        "وسأحذف الصفحات المتكررة وأعيده لك PDF واحداً مرتباً."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("يرجى إرسال ملف PDF فقط.")
        return

    user = update.effective_user
    logger.info(f"Received PDF from {user.id}: {document.file_name}")

    # تحميل الملف
    input_path = os.path.join(TEMP_DIR, document.file_name)
    file = await document.get_file()
    await file.download_to_drive(input_path)

    processing_msg = await update.message.reply_text("⏳ جاري تحليل الصفحات وإزالة التكرار...")

    try:
        # قراءة الإعدادات من متغيرات البيئة
        threshold = int(os.getenv("HAMMING_THRESHOLD", 8))
        dpi = int(os.getenv("DPI", 120))

        dedup = PdfDeduplicator(threshold=threshold, dpi=dpi)

        # تشغيل المعالجة في Thread عشان ما توقفش البوت
        loop = asyncio.get_running_loop()
        output_path = os.path.join(TEMP_DIR, "deduped_" + document.file_name)

        total, kept = await loop.run_in_executor(
            None,
            dedup.deduplicate,
            input_path,
            output_path
        )

        await processing_msg.edit_text(
            f"✅ انتهت المعالجة: {total} صفحة → {kept} صفحة فريدة."
        )

        # إرسال الملف المُعالج
        with open(output_path, "rb") as f:
            await update.message.reply_document(
                f,
                filename=f"clean_{document.file_name}",
                caption=f"📎 تم حذف {total - kept} صفحة مكررة."
            )

    except Exception as e:
        logger.exception("Error processing PDF")
        await update.message.reply_text(f"❌ حدث خطأ: {e}")
    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(input_path):
            os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
