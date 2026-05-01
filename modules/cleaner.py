import re

NOISE_WORDS = {"iiii", "titti", "tiitti", "1111", "||||", "lill", "illl", "llli", "tttti", "ttti"}


def clean_customer_name(text: str) -> str | None:
    if not text:
        return None

    words = text.split()
    filtered = [w for w in words if w.lower() not in NOISE_WORDS]
    text_joined = " ".join(filtered)

    # A person's name on MSEDCL bill is usually 2+ words, mostly alphabetic.
    matches = re.findall(r"(?:[A-Za-z]{2,}\s*){2,}", text_joined)

    if not matches:
        clean_fallback = re.sub(r"[^A-Za-z\s]", " ", text_joined)
        clean_fallback = re.sub(r"\s+", " ", clean_fallback).strip()
        return clean_fallback if len(clean_fallback) > 3 else None

    best_match = max(matches, key=len).strip()
    return best_match


def clean_ocr_text(text: str) -> str:
    """General cleanup for OCR garbage."""
    text = re.sub(r"[^\w\s\.,\-\/\|:]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
