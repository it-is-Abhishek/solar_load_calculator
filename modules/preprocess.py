from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def preprocess_image_for_ocr(image_path: Path) -> Image.Image:
    image = cv2.imread(str(image_path))
    if image is None:
        return Image.open(image_path).convert("RGB")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray)
    blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
    thresholded = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    coords = np.column_stack(np.where(thresholded > 0))
    if coords.size:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        (height, width) = thresholded.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        thresholded = cv2.warpAffine(
            thresholded,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    return Image.fromarray(thresholded)
