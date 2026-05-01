from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


def read_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        pil_image = Image.open(image_path).convert("RGB")
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return image


def preprocess_image_for_ocr(image_path: Path) -> Image.Image:
    image = read_image(image_path)
    processed = enhance_document_image(image)
    return Image.fromarray(processed)


def enhance_document_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=18)
    contrasted = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(denoised)
    blurred = cv2.GaussianBlur(contrasted, (3, 3), 0)
    sharpened = cv2.addWeighted(contrasted, 1.4, blurred, -0.4, 0)
    thresholded = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )
    return deskew_binary_image(thresholded)


def deskew_binary_image(image: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(image < 250))
    if coords.size == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def crop_msedcl_regions(image: np.ndarray) -> dict[str, np.ndarray]:
    height, width = image.shape[:2]
    # Hard-cut bottom 35% — ads, QR codes, solar banners, payment footers live there
    top_cutoff = int(height * 0.65)
    working = image[:top_cutoff, :]

    wh = working.shape[0]
    ww = working.shape[1]

    regions = {
        "full_clean": working,
        # Customer name, billing month — top-left block
        "header_left": working[0:int(wh * 0.20), 0:int(ww * 0.60)],
        # Consumer number, name continuation
        "consumer_block": working[int(wh * 0.06):int(wh * 0.24), int(ww * 0.02):int(ww * 0.60)],
        # Bill amount, due date — top-right
        "header_right": working[0:int(wh * 0.24), int(ww * 0.58):ww],
        # Middle table: readings, units, charges
        "usage_table": working[int(wh * 0.22):int(wh * 0.58), int(ww * 0.02):int(ww * 0.98)],
        # Connected load and tariff — left-middle
        "load_tariff": working[int(wh * 0.22):int(wh * 0.40), int(ww * 0.02):int(ww * 0.65)],
        # Meter number — centre strip
        "meter_block": working[int(wh * 0.26):int(wh * 0.52), int(ww * 0.25):int(ww * 0.80)],
        # Previous/current readings and units consumed
        "readings_block": working[int(wh * 0.28):int(wh * 0.65), int(ww * 0.02):int(ww * 0.98)],
    }
    return regions


def build_region_payload(image_path: Path) -> dict[str, Any]:
    raw_bgr = read_image(image_path)
    enhanced = enhance_document_image(raw_bgr)
    regions = crop_msedcl_regions(enhanced)
    preview = Image.fromarray(enhanced)
    return {
        "preview_image": preview,
        "regions": {name: Image.fromarray(region) for name, region in regions.items()},
    }
