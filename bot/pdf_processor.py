import os
import tempfile
import fitz  # PyMuPDF
import imagehash
from PIL import Image
from utils.logger import setup_logger

logger = setup_logger(__name__)

class PdfDeduplicator:
    def __init__(self, threshold=8, dpi=120):
        self.threshold = threshold
        self.dpi = dpi

    def deduplicate(self, input_pdf_path, output_pdf_path):
        """
        فتح PDF، مقارنة الصفحات باستخدام perceptual hash،
        وبناء PDF جديد بالصفحات الفريدة فقط (بالترتيب).
        يُرجع عدد الصفحات الكلي وعدد الصفحات الفريدة.
        """
        doc = fitz.open(input_pdf_path)
        total_pages = doc.page_count
        unique_hashes = []  # لتخزين هاشات الصفحات اللي فاتت
        kept_pages = 0

        # إنشاء مستند PDF جديد
        output_doc = fitz.open()

        for page_num in range(total_pages):
            page = doc.load_page(page_num)

            # 1. تحويل الصفحة إلى صورة
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 2. حساب الهاش (phash)
            h = imagehash.phash(img)
            hash_hex = str(h)

            # 3. هل الهاش قريب من أي هاش سابق؟
            duplicate = False
            for prev_hash_hex in unique_hashes:
                prev_hash = imagehash.hex_to_hash(prev_hash_hex)
                distance = h - prev_hash
                if distance <= self.threshold:
                    logger.info(f"Page {page_num+1}: Duplicate (distance {distance})")
                    duplicate = True
                    break

            if duplicate:
                continue

            # صفحة جديدة فريدة ➜ نضيفها للـ PDF الجديد
            unique_hashes.append(hash_hex)
            # إعادة تضمين الصفحة كاملة (بنفس الحجم) عشان تبقى واضحة
            output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            kept_pages += 1
            logger.info(f"Page {page_num+1}: Added as new slide")

        # حفظ المستند الجديد
        output_doc.save(output_pdf_path)
        output_doc.close()
        doc.close()

        return total_pages, kept_pages
