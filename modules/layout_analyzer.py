from __future__ import annotations

import cv2
import numpy as np


def crop_msedcl_regions(image: np.ndarray) -> dict[str, np.ndarray]:
    height, width = image.shape[:2]
    top_cutoff = int(height * 0.65)
    working = image[:top_cutoff, :]

    wh = working.shape[0]
    ww = working.shape[1]

    return {
        "full_clean": working,
        "header_left": working[0:int(wh * 0.20), 0:int(ww * 0.60)],
        "consumer_block": working[int(wh * 0.06):int(wh * 0.24), int(ww * 0.02):int(ww * 0.60)],
        "header_right": working[0:int(wh * 0.24), int(ww * 0.58):ww],
        "usage_table": working[int(wh * 0.22):int(wh * 0.58), int(ww * 0.02):int(ww * 0.98)],
        "load_tariff": working[int(wh * 0.22):int(wh * 0.40), int(ww * 0.02):int(ww * 0.65)],
        "meter_block": working[int(wh * 0.26):int(wh * 0.52), int(ww * 0.25):int(ww * 0.80)],
        "readings_block": working[int(wh * 0.28):int(wh * 0.65), int(ww * 0.02):int(ww * 0.98)],
    }


def crop_tata_power_regions(image: np.ndarray) -> dict[str, np.ndarray]:
    height, width = image.shape[:2]
    # Tata Power bills usually have header up to 30%, tables in the middle.
    working = image[:int(height * 0.70), :]
    wh, ww = working.shape[:2]

    return {
        "full_clean": working,
        "header_left": working[0:int(wh * 0.30), 0:int(ww * 0.50)],
        "header_right": working[0:int(wh * 0.30), int(ww * 0.50):ww],
        "consumer_block": working[int(wh * 0.10):int(wh * 0.30), 0:int(ww * 0.50)],
        "usage_table": working[int(wh * 0.30):int(wh * 0.60), :],
        "load_tariff": working[int(wh * 0.20):int(wh * 0.40), :],
        "meter_block": working[int(wh * 0.20):int(wh * 0.50), :],
        "readings_block": working[int(wh * 0.30):int(wh * 0.60), :],
    }


def crop_generic_regions(image: np.ndarray) -> dict[str, np.ndarray]:
    # Generic fallback: slice into logical bands
    height, width = image.shape[:2]
    working = image[:int(height * 0.80), :]
    wh, ww = working.shape[:2]

    return {
        "full_clean": working,
        "header_left": working[0:int(wh * 0.30), 0:int(ww * 0.50)],
        "header_right": working[0:int(wh * 0.30), int(ww * 0.50):ww],
        "consumer_block": working[0:int(wh * 0.30), 0:ww],
        "usage_table": working[int(wh * 0.30):int(wh * 0.70), :],
        "load_tariff": working[int(wh * 0.20):int(wh * 0.50), :],
        "meter_block": working[int(wh * 0.20):int(wh * 0.60), :],
        "readings_block": working[int(wh * 0.30):int(wh * 0.70), :],
    }


def segment_document(image: np.ndarray, provider: str) -> dict[str, np.ndarray]:
    """
    Dynamically route the image to the correct layout segmenter based on provider.
    """
    if provider == "MSEDCL":
        return crop_msedcl_regions(image)
    elif provider == "TATA_POWER":
        return crop_tata_power_regions(image)
    else:
        return crop_generic_regions(image)
