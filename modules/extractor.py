from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pdfplumber
import pytesseract
from PIL import Image
from PIL import ImageOps

from modules.preprocess import preprocess_image_for_ocr

try:
    import easyocr  # type: ignore
except ImportError:  # pragma: no cover
    easyocr = None

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


class BillExtractor:
    def __init__(self, logger):
        self.logger = logger
        self._easyocr_reader = None

    def _get_easyocr_reader(self):
        if easyocr is None:
            return None
        if self._easyocr_reader is None:
            self._easyocr_reader = easyocr.Reader(["en"], gpu=False)
        return self._easyocr_reader

    def extract_text_from_pdf(self, file_path: Path) -> dict[str, Any]:
        self.logger.info("Extracting text from PDF: %s", file_path.name)
        text_chunks: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_chunks.append(page_text)

        method = "pdf_text"
        if text_chunks:
            return {
                "text": "\n".join(text_chunks),
                "ocr_confidence": 1.0,
                "method": method,
                "preview_image": self.render_pdf_first_page(file_path),
            }

        self.logger.info("No embedded PDF text found, switching to OCR for %s", file_path.name)
        image = self.render_pdf_first_page(file_path)
        if image is None:
            return {"text": "", "ocr_confidence": 0.0, "method": "pdf_ocr", "preview_image": None}

        ocr_result = self._ocr_image(image)
        ocr_result["method"] = "pdf_ocr"
        ocr_result["preview_image"] = image
        return ocr_result

    def render_pdf_first_page(self, file_path: Path) -> Image.Image | None:
        if fitz is None:
            return None
        document = fitz.open(file_path)
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
        document.close()
        return image

    def extract_text_from_image(self, file_path: Path) -> dict[str, Any]:
        self.logger.info("Extracting text from image: %s", file_path.name)
        preprocessed_image = preprocess_image_for_ocr(file_path)
        result = self._ocr_image(preprocessed_image)
        result["preview_image"] = preprocessed_image
        result["method"] = "image_ocr"
        return result

    def _ocr_image(self, image: Image.Image) -> dict[str, Any]:
        reader = self._get_easyocr_reader()
        if reader is not None:
            self.logger.info("Using EasyOCR engine")
            variants = self._build_easyocr_variants(image)
            primary_entries = reader.readtext(
                self._image_to_array(variants[0]),
                detail=1,
                paragraph=False,
            )
            ocr_entries = primary_entries
            if len(primary_entries) < 35 and len(variants) > 1:
                secondary_entries = reader.readtext(
                    self._image_to_array(variants[1]),
                    detail=1,
                    paragraph=False,
                )
                if len(secondary_entries) > len(ocr_entries):
                    ocr_entries = secondary_entries

            text = self._entries_to_lines(ocr_entries)
            confidences = [float(entry[2]) for entry in ocr_entries if len(entry) > 2]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return {"text": text, "ocr_confidence": round(confidence, 3), "engine": "easyocr"}

        self.logger.info("Using Tesseract OCR engine")
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )
        words = [word for word in ocr_data["text"] if word.strip()]
        text = " ".join(words)
        confidences = [
            float(conf)
            for conf in ocr_data["conf"]
            if isinstance(conf, (int, float, str)) and str(conf).strip() not in {"-1", ""}
        ]
        confidence = (
            sum(confidences) / (len(confidences) * 100)
            if confidences
            else 0.0
        )
        return {"text": text, "ocr_confidence": round(confidence, 3), "engine": "tesseract"}

    @staticmethod
    def _image_to_array(image: Image.Image):
        import numpy as np

        return np.array(image)

    @staticmethod
    def _build_easyocr_variants(image: Image.Image) -> list[Image.Image]:
        rgb = image.convert("RGB")
        gray = ImageOps.grayscale(rgb)
        gray = ImageOps.autocontrast(gray)
        variants = [
            rgb,
            gray.resize((gray.width * 2, gray.height * 2)),
        ]
        deduped: list[Image.Image] = []
        seen_sizes: set[tuple[int, int, str]] = set()
        for variant in variants:
            mode_key = f"{variant.mode}"
            key = (variant.width, variant.height, mode_key)
            if key not in seen_sizes:
                seen_sizes.add(key)
                deduped.append(variant)
        return deduped

    @staticmethod
    def _entries_to_lines(entries: list[tuple[Any, str, float]]) -> str:
        if not entries:
            return ""

        normalized = []
        for box, text, conf in entries:
            if not text or not str(text).strip():
                continue
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            normalized.append(
                {
                    "text": str(text).strip(),
                    "conf": float(conf),
                    "x": min(xs),
                    "y": min(ys),
                    "h": max(ys) - min(ys),
                }
            )

        normalized.sort(key=lambda item: (item["y"], item["x"]))
        lines: list[list[dict[str, Any]]] = []
        for item in normalized:
            if not lines:
                lines.append([item])
                continue
            last_line = lines[-1]
            avg_y = sum(entry["y"] for entry in last_line) / len(last_line)
            avg_h = max(sum(entry["h"] for entry in last_line) / len(last_line), 12)
            if abs(item["y"] - avg_y) <= avg_h * 0.7:
                last_line.append(item)
            else:
                lines.append([item])

        text_lines = []
        for line in lines:
            line.sort(key=lambda item: item["x"])
            merged = " ".join(item["text"] for item in line)
            text_lines.append(merged)
        return "\n".join(text_lines)

    def process_file(self, file_path: Path) -> dict[str, Any]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self.extract_text_from_pdf(file_path)
        return self.extract_text_from_image(file_path)
