from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pdfplumber
import pytesseract
from PIL import Image, ImageOps

from modules.preprocess import build_region_payload

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

        preview_image = self.render_pdf_first_page(file_path)
        if text_chunks:
            return {
                "text": "\n".join(text_chunks),
                "region_texts": {},
                "ocr_confidence": 1.0,
                "method": "pdf_text",
                "preview_image": preview_image,
                "engine": "embedded_pdf_text",
            }

        self.logger.info("No embedded PDF text found, switching to region OCR for %s", file_path.name)
        if preview_image is None:
            return {
                "text": "",
                "region_texts": {},
                "ocr_confidence": 0.0,
                "method": "pdf_ocr",
                "preview_image": None,
                "engine": "n/a",
            }

        return self._ocr_image_regions(preview_image, method="pdf_ocr")

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
        payload = build_region_payload(file_path)
        preview_image = payload["preview_image"]
        region_images = payload["regions"]
        return self._ocr_regions(region_images, preview_image=preview_image, method="image_ocr")

    def _ocr_image_regions(self, image: Image.Image, method: str) -> dict[str, Any]:
        temp_path = Path("/tmp/_msedcl_temp_preview.png")
        image.save(temp_path)
        payload = build_region_payload(temp_path)
        return self._ocr_regions(payload["regions"], preview_image=payload["preview_image"], method=method)

    def _ocr_regions(
        self,
        region_images: dict[str, Image.Image],
        preview_image: Image.Image,
        method: str,
    ) -> dict[str, Any]:
        region_texts: dict[str, str] = {}
        region_confidences: list[float] = []
        reader = self._get_easyocr_reader()

        for region_name, region_image in region_images.items():
            if reader is not None:
                entries = reader.readtext(
                    self._image_to_array(self._prepare_variant(region_image)),
                    detail=1,
                    paragraph=False,
                )
                text, confidence = self._entries_to_lines(entries)
                region_texts[region_name] = text
                if confidence > 0:
                    region_confidences.append(confidence)
            else:
                text, confidence = self._tesseract_region(region_image)
                region_texts[region_name] = text
                if confidence > 0:
                    region_confidences.append(confidence)

        ordered_sections = [
            "header_left",
            "consumer_block",
            "header_right",
            "load_tariff",
            "meter_block",
            "usage_table",
            "readings_block",
        ]
        merged_text = "\n".join(
            region_texts.get(section, "")
            for section in ordered_sections
            if region_texts.get(section, "").strip()
        )
        average_confidence = (
            round(sum(region_confidences) / len(region_confidences), 3)
            if region_confidences
            else 0.0
        )
        return {
            "text": merged_text,
            "region_texts": region_texts,
            "ocr_confidence": average_confidence,
            "method": method,
            "preview_image": preview_image,
            "engine": "easyocr" if reader is not None else "tesseract",
        }

    def _tesseract_region(self, region_image: Image.Image) -> tuple[str, float]:
        ocr_data = pytesseract.image_to_data(
            region_image,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )
        words = [word.strip() for word in ocr_data["text"] if word.strip()]
        confidences = [
            float(conf)
            for conf in ocr_data["conf"]
            if str(conf).strip() not in {"-1", ""}
        ]
        confidence = sum(confidences) / (len(confidences) * 100) if confidences else 0.0
        return " ".join(words), round(confidence, 3)

    @staticmethod
    def _prepare_variant(image: Image.Image) -> Image.Image:
        gray = ImageOps.grayscale(image)
        gray = ImageOps.autocontrast(gray)
        return gray.resize((gray.width * 2, gray.height * 2))

    @staticmethod
    def _image_to_array(image: Image.Image):
        import numpy as np

        return np.array(image)

    @staticmethod
    def _entries_to_lines(entries: list[tuple[Any, str, float]]) -> tuple[str, float]:
        if not entries:
            return "", 0.0

        normalized = []
        confidences = []
        for box, text, conf in entries:
            clean_text = str(text).strip()
            if not clean_text:
                continue
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            confidences.append(float(conf))
            normalized.append(
                {
                    "text": clean_text,
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
            text_lines.append(" ".join(item["text"] for item in line))

        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return "\n".join(text_lines), round(confidence, 3)

    def process_file(self, file_path: Path) -> dict[str, Any]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self.extract_text_from_pdf(file_path)
        return self.extract_text_from_image(file_path)
