import os
import cv2
import tempfile
import imagehash
from PIL import Image
from utils.logger import setup_logger

logger = setup_logger(__name__)

class VideoToPdf:
    def __init__(self, threshold=10, frame_interval=2, dpi=120):
        self.threshold = threshold
        self.frame_interval = frame_interval
        self.dpi = dpi

    def extract_unique_frames(self, video_path):
        """
        استخراج الإطارات الفريدة من الفيديو،
        تُرجع قائمة بمسارات الصور الفريدة (PNG).
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("لم يتم فتح الفيديو")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25  # افتراضي

        prev_hash = None
        unique_hashes = []
        saved_images = []
        frame_idx = 0

        temp_dir = tempfile.mkdtemp(prefix="video_frames_")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # التقاط إطار كل `frame_interval` ثانية
            if frame_idx % int(fps * self.frame_interval) == 0:
                # تحويل BGR (OpenCV) إلى RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)

                # حساب dhash
                h = imagehash.dhash(pil_img)
                h_str = str(h)

                # مقارنة بالإطار السابق
                if prev_hash is not None:
                    diff = h - prev_hash
                    if diff <= self.threshold:
                        # متشابه جداً، تجاهل
                        frame_idx += 1
                        continue

                # إطار جديد فريد
                unique_hashes.append(h_str)
                img_path = os.path.join(temp_dir, f"slide_{frame_idx:05d}.png")
                pil_img.save(img_path)
                saved_images.append(img_path)
                prev_hash = h

            frame_idx += 1

        cap.release()
        logger.info(f"Extracted {len(saved_images)} unique frames out of {frame_idx} frames checked")
        return saved_images

    def images_to_pdf(self, image_paths, output_pdf_path):
        """تجميع الصور في PDF باستخدام PyMuPDF"""
        import fitz
        doc = fitz.open()
        for img_path in image_paths:
            img = fitz.open(img_path)
            rect = fitz.Rect(0, 0, img.width, img.height)
            page = doc.new_page(width=img.width, height=img.height)
            page.insert_image(rect, filename=img_path)
            img.close()
        doc.save(output_pdf_path)
        doc.close()
