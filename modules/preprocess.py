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
    top_cutoff = int(height * 0.72)
    working = image[:top_cutoff, :]

    wh = working.shape[0]
    ww = working.shape[1]

    regions = {
        "full_clean": working,
        "header_left": working[0:int(wh * 0.22), 0:int(ww * 0.62)],
        "consumer_block": working[int(wh * 0.07):int(wh * 0.26), int(ww * 0.02):int(ww * 0.62)],
        "header_right": working[0:int(wh * 0.25), int(ww * 0.56):ww],
        "usage_table": working[int(wh * 0.24):int(wh * 0.60), int(ww * 0.02):int(ww * 0.98)],
        "load_tariff": working[int(wh * 0.24):int(wh * 0.42), int(ww * 0.02):int(ww * 0.70)],
        "meter_block": working[int(wh * 0.28):int(wh * 0.55), int(ww * 0.28):int(ww * 0.84)],
        "readings_block": working[int(wh * 0.30):int(wh * 0.68), int(ww * 0.02):int(ww * 0.98)],
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
