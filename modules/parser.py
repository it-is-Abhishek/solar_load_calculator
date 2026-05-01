from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


FIELD_TYPES = {
    "customer_name": "text",
    "consumer_number": "id",
    "billing_month": "text",
    "bill_amount": "currency",
    "units_consumed": "numeric",
    "connected_load_kw": "numeric",
    "tariff_category": "text",
    "meter_number": "id",
    "due_date": "date",
    "current_reading": "numeric",
    "previous_reading": "numeric",
}

FIELD_REGION_PRIORITY = {
    "customer_name": ["header_left", "consumer_block", "full_text"],
    "consumer_number": ["consumer_block", "header_left", "full_text"],
    "billing_month": ["header_left", "header_right", "full_text"],
    "bill_amount": ["header_right", "full_text"],
    "units_consumed": ["readings_block", "usage_table", "full_text"],
    "connected_load_kw": ["load_tariff", "usage_table", "full_text"],
    "tariff_category": ["load_tariff", "usage_table", "full_text"],
    "meter_number": ["meter_block", "usage_table", "full_text"],
    "due_date": ["header_right", "full_text"],
    "current_reading": ["readings_block", "usage_table", "full_text"],
    "previous_reading": ["readings_block", "usage_table", "full_text"],
}

LABEL_PATTERNS = {
    "customer_name": [
        r"(?:consumer\s*name|customer\s*name|name\s*of\s*consumer|ग्राहकाचे\s*नाव)\s*[:\-]?\s*([A-Z][A-Z\s\.]{4,60})",
    ],
    "consumer_number": [
        r"(?:consumer\s*no|consumer\s*number|service\s*no|ग्राहक\s*क्रमांक)\s*[:\-]?\s*([0-9]{10,13})",
    ],
    "billing_month": [
        r"(?:bill\s*of\s*supply\s*for\s*the\s*month\s*of|billing\s*month|bill\s*month|महिना)\s*[:\-]?\s*([A-Za-z0-9\-\/ ]{5,20})",
    ],
    "bill_amount": [
        r"(?:bill\s*amount|amount\s*payable|current\s*bill\s*amount|देयक\s*रक्कम)\s*[:\-]?\s*(?:rs\.?|₹)?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "units_consumed": [
        r"(?:units\s*consumed|total\s*units|energy\s*consumed|एकूण\s*वापर)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "connected_load_kw": [
        r"(?:connected\s*load|sanctioned\s*load|मंजूर\s*भार)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)\s*(?:kw|kva)?",
    ],
    "tariff_category": [
        r"(?:tariff\s*category|tariff|category|दर\s*प्रकार)\s*[:\-]?\s*([A-Za-z0-9\-\s\/]{3,40})",
    ],
    "meter_number": [
        r"(?:meter\s*no|meter\s*number|मीटर\s*क्रमांक)\s*[:\-]?\s*([A-Za-z0-9\-]{8,16})",
    ],
    "due_date": [
        r"(?:due\s*date|payment\s*due\s*date|देय\s*दिनांक)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
    ],
    "current_reading": [
        r"(?:current\s*reading|present\s*reading|चालू\s*रिडिंग)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
    "previous_reading": [
        r"(?:previous\s*reading|past\s*reading|मागील\s*रिडिंग)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
    ],
}

MONTH_MAP = {
    "jan": "JAN",
    "feb": "FEB",
    "mar": "MAR",
    "apr": "APR",
    "may": "MAY",
    "jun": "JUN",
    "jul": "JUL",
    "aug": "AUG",
    "sep": "SEP",
    "oct": "OCT",
    "nov": "NOV",
    "dec": "DEC",
}

PHONE_BLACKLIST = {"7798577985", "77985", "9112233120"}


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x0c", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def clean_text(value: str) -> str:
    return re.sub(r"\s{2,}", " ", value).strip(" :.-")


def clean_currency(value: str) -> float | None:
    candidate = value.replace(",", "").replace("₹", "").replace("Rs.", "").replace("INR", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", candidate)
    return float(match.group()) if match else None


def clean_number(value: str) -> float | int | None:
    candidate = value.replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", candidate)
    if not match:
        return None
    number = float(match.group())
    return int(number) if number.is_integer() else round(number, 2)


def score_field_confidence(field: str, value: Any, source: str, region_name: str) -> float:
    if value in (None, ""):
        return 0.0

    source_scores = {
        "label_regex": 0.93,
        "positional": 0.81,
        "heuristic": 0.68,
    }
    region_bonus = {
        "header_left": 0.03,
        "consumer_block": 0.03,
        "header_right": 0.03,
        "readings_block": 0.03,
        "load_tariff": 0.03,
        "usage_table": 0.02,
        "full_text": 0.0,
    }
    score = source_scores.get(source, 0.5) + region_bonus.get(region_name, 0.0)
    field_type = FIELD_TYPES.get(field, "text")

    if field_type == "currency" and isinstance(value, (int, float)) and 100 <= float(value) <= 50000:
        score += 0.03
    if field_type == "numeric" and isinstance(value, (int, float)):
        score += 0.02
    if field == "connected_load_kw" and isinstance(value, (int, float)) and 0.5 <= float(value) <= 5:
        score += 0.06
    if field == "units_consumed" and isinstance(value, (int, float)) and 10 <= float(value) <= 2500:
        score += 0.04
    if field_type == "date" and isinstance(value, str) and re.fullmatch(r"\d{2}[/-]\d{2}[/-]\d{4}", value):
        score += 0.03
    if field_type == "id" and len(re.sub(r"\D", "", str(value))) >= 8:
        score += 0.03

    return round(min(score, 0.99), 3)


def fuzzy_month(token: str) -> str | None:
    cleaned = re.sub(r"[^a-z]", "", token.lower())
    if len(cleaned) < 3:
        return None
    best_key = None
    best_score = 0.0
    for key in MONTH_MAP:
        score = SequenceMatcher(None, cleaned[:3], key).ratio()
        if score > best_score:
            best_key = key
            best_score = score
    return MONTH_MAP[best_key] if best_key and best_score >= 0.55 else None


def build_search_space(raw_text: str, region_texts: dict[str, str] | None = None) -> dict[str, str]:
    space = {"full_text": raw_text}
    if region_texts:
        for key, value in region_texts.items():
            space[key] = value or ""
    return space


def extract_with_patterns(text: str, patterns: list[str], field: str) -> tuple[Any, str | None]:
    transformers = {
        "customer_name": clean_text,
        "consumer_number": clean_text,
        "billing_month": clean_text,
        "bill_amount": clean_currency,
        "units_consumed": clean_number,
        "connected_load_kw": clean_number,
        "tariff_category": clean_text,
        "meter_number": clean_text,
        "due_date": clean_text,
        "current_reading": clean_number,
        "previous_reading": clean_number,
    }
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw_value = match.group(1)
            value = transformers[field](raw_value)
            return value, pattern
    return None, None


def reject_phone_like(field: str, value: Any) -> bool:
    digits = re.sub(r"\D", "", str(value))
    if digits in PHONE_BLACKLIST:
        return True
    if field in {"bill_amount", "units_consumed", "connected_load_kw", "current_reading", "previous_reading"}:
        return False
    return len(digits) == 10 and digits.startswith(("7", "8", "9"))


def infer_customer_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = []
    for line in lines[:8]:
        if re.search(r"\d", line):
            continue
        clean_line = re.sub(r"[^A-Za-z\s]", " ", line)
        words = [word for word in clean_line.split() if len(word) > 2]
        if len(words) >= 2:
            uppercase_ratio = sum(1 for word in words if word.upper() == word) / len(words)
            if uppercase_ratio >= 0.5:
                candidates.append(" ".join(words))
    return max(candidates, key=len) if candidates else None


def infer_consumer_number(text: str) -> str | None:
    numbers = [value for value in re.findall(r"\b\d{10,13}\b", text) if not reject_phone_like("consumer_number", value)]
    return numbers[0] if numbers else None


def infer_billing_month(text: str) -> str | None:
    for token in re.findall(r"\b[A-Za-z0-9]{3,12}[-/ ]20\d{2}\b", text):
        year_match = re.search(r"(20\d{2})", token)
        month = fuzzy_month(token)
        if month and year_match:
            return f"{month}-{year_match.group(1)}"

    month_of_match = re.search(r"month\s*of\s*([A-Za-z]{3,12})", text, flags=re.IGNORECASE)
    year_match = re.search(r"(20\d{2})", text)
    if month_of_match and year_match:
        month = fuzzy_month(month_of_match.group(1))
        if month:
            return f"{month}-{year_match.group(1)}"

    for token in re.findall(r"[A-Za-z]{3,12}[ -/]?\d{4}", text):
        month = fuzzy_month(token)
        year_match = re.search(r"(20\d{2})", token)
        if month and year_match:
            return f"{month}-{year_match.group(1)}"
    return None


def infer_due_date(text: str) -> str | None:
    candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text.replace("+", "-"))
    valid = []
    for date in candidates:
        day, month, year = map(int, re.split(r"[/-]", date))
        if 1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2035:
            valid.append(date)
    return valid[0] if valid else None


def infer_bill_amount(text: str) -> float | None:
    amounts = []
    for token in re.findall(r"\b\d{3,6}[.,]\d{2}\b", text):
        normalized = token.replace(",", ".") if token.count(",") == 1 and "." not in token else token
        value = clean_currency(normalized)
        if value and 100 <= value <= 50000:
            amounts.append(value)
    return amounts[0] if amounts else None


def infer_connected_load(text: str) -> float | None:
    compact = re.sub(r"(?<=\d)\s+(?=\d)", ".", text)
    kw_match = re.search(r"\b(\d(?:\.\d{1,2})?)\s*kw\b", compact, flags=re.IGNORECASE)
    if kw_match:
        value = clean_number(kw_match.group(1))
        if isinstance(value, (int, float)) and 0.5 <= float(value) <= 5:
            return float(value)
    return None


def infer_tariff(text: str) -> str | None:
    match = re.search(r"\b(?:LT|HT)[-\s]?[A-Z0-9]*\s*(?:Residential|Res|Commercial|Comm)?\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    value = clean_text(match.group(0).replace("Res", "Residential"))
    return value


def infer_meter_number(text: str, consumer_number: str | None) -> str | None:
    candidates = re.findall(r"\b\d{8,12}\b", text)
    filtered = [value for value in candidates if value != consumer_number and not reject_phone_like("meter_number", value)]
    return filtered[0] if filtered else None


def infer_reading_triplet(text: str) -> tuple[int | None, int | None, int | None]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        numbers = [int(token.replace(",", "")) for token in re.findall(r"\b\d{2,6}\b", line)]
        plausible = [value for value in numbers if value < 100000]
        if len(plausible) >= 3:
            high = sorted(plausible)[-3:]
            prev, curr = sorted(high[:2])
            units = high[2] - curr if high[2] > curr else None
            if curr > prev:
                diff = curr - prev
                if 1 <= diff <= 2500:
                    return prev, curr, diff

    numbers = [int(token) for token in re.findall(r"\b\d{2,6}\b", text)]
    reading_candidates = [value for value in numbers if 1000 <= value <= 99999 and not (2020 <= value <= 2035)]
    current = max(reading_candidates) if reading_candidates else None
    previous = None
    if current is not None:
        lower = [value for value in reading_candidates if value < current]
        previous = max(lower) if lower else None
    units = current - previous if current and previous and 1 <= current - previous <= 2500 else None

    plausible_units = [value for value in numbers if 10 <= value <= 2500 and not reject_phone_like("units_consumed", value)]
    if units is None and plausible_units:
        units = max(plausible_units)
    return previous, current, units


def extract_field(field: str, search_space: dict[str, str]) -> dict[str, Any]:
    for region_name in FIELD_REGION_PRIORITY[field]:
        text = search_space.get(region_name, "")
        if not text.strip():
            continue
        value, pattern = extract_with_patterns(text, LABEL_PATTERNS[field], field)
        if value not in (None, "") and not reject_phone_like(field, value):
            value = sanitize_value(field, value)
            if value in (None, ""):
                continue
            return {
                "value": value,
                "confidence": score_field_confidence(field, value, "label_regex", region_name),
                "source": f"label_regex:{region_name}",
                "matched_pattern": pattern,
                "region": region_name,
            }
    return {
        "value": None,
        "confidence": 0.0,
        "source": "unresolved",
        "matched_pattern": None,
        "region": None,
    }


def sanitize_value(field: str, value: Any) -> Any:
    if value in (None, ""):
        return None

    if field == "bill_amount":
        return value if isinstance(value, (int, float)) and 100 <= float(value) <= 50000 else None
    if field == "units_consumed":
        return value if isinstance(value, (int, float)) and 10 <= float(value) <= 2500 else None
    if field == "connected_load_kw":
        return value if isinstance(value, (int, float)) and 0.5 <= float(value) <= 5 else None
    if field in {"current_reading", "previous_reading"}:
        return value if isinstance(value, (int, float)) and 1000 <= float(value) <= 99999 else None
    if field == "due_date" and isinstance(value, str):
        match = re.fullmatch(r"(\d{2})[/-](\d{2})[/-](\d{4})", value)
        if not match:
            return None
        day, month, year = map(int, match.groups())
        current_year = datetime.now().year
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= current_year + 1):
            return None
        return value
    if field in {"consumer_number", "meter_number"} and reject_phone_like(field, value):
        return None
    return value


def parse_bill_data(raw_text: str, region_texts: dict[str, str] | None = None) -> dict[str, dict[str, Any]]:
    region_space = {
        key: normalize_whitespace(value)
        for key, value in build_search_space(raw_text, region_texts).items()
    }

    results = {
        field: extract_field(field, region_space)
        for field in FIELD_TYPES
    }

    header_text = "\n".join(region_space.get(key, "") for key in ["header_left", "consumer_block", "header_right"])
    readings_text = "\n".join(region_space.get(key, "") for key in ["readings_block", "usage_table"])
    load_text = "\n".join(region_space.get(key, "") for key in ["load_tariff", "usage_table"])

    if not results["customer_name"]["value"]:
        name = infer_customer_name(header_text or region_space["full_text"])
        if name:
            name = sanitize_value("customer_name", name)
        if name:
            results["customer_name"] = {
                "value": name,
                "confidence": score_field_confidence("customer_name", name, "heuristic", "header_left"),
                "source": "heuristic:header_left",
                "matched_pattern": "uppercase_name_heuristic",
                "region": "header_left",
            }

    if not results["consumer_number"]["value"]:
        consumer = infer_consumer_number(region_space.get("consumer_block", "") or region_space["full_text"])
        if consumer:
            consumer = sanitize_value("consumer_number", consumer)
        if consumer:
            results["consumer_number"] = {
                "value": consumer,
                "confidence": score_field_confidence("consumer_number", consumer, "heuristic", "consumer_block"),
                "source": "heuristic:consumer_block",
                "matched_pattern": "consumer_digit_heuristic",
                "region": "consumer_block",
            }

    if not results["billing_month"]["value"]:
        month = infer_billing_month(header_text or region_space["full_text"])
        if month:
            month = sanitize_value("billing_month", month)
        if month:
            results["billing_month"] = {
                "value": month,
                "confidence": score_field_confidence("billing_month", month, "heuristic", "header_left"),
                "source": "heuristic:header_left",
                "matched_pattern": "month_of_bill_heuristic",
                "region": "header_left",
            }

    if not results["bill_amount"]["value"]:
        amount = infer_bill_amount(region_space.get("header_right", "") or region_space["full_text"])
        if amount:
            amount = sanitize_value("bill_amount", amount)
        if amount:
            results["bill_amount"] = {
                "value": amount,
                "confidence": score_field_confidence("bill_amount", amount, "heuristic", "header_right"),
                "source": "heuristic:header_right",
                "matched_pattern": "amount_range_heuristic",
                "region": "header_right",
            }

    if not results["due_date"]["value"]:
        due_date = infer_due_date(region_space.get("header_right", "") or region_space["full_text"])
        if due_date:
            due_date = sanitize_value("due_date", due_date)
        if due_date:
            results["due_date"] = {
                "value": due_date,
                "confidence": score_field_confidence("due_date", due_date, "heuristic", "header_right"),
                "source": "heuristic:header_right",
                "matched_pattern": "valid_date_heuristic",
                "region": "header_right",
            }

    if not results["connected_load_kw"]["value"]:
        load = infer_connected_load(load_text or region_space["full_text"])
        if load is not None:
            load = sanitize_value("connected_load_kw", load)
        if load is not None:
            results["connected_load_kw"] = {
                "value": load,
                "confidence": score_field_confidence("connected_load_kw", load, "heuristic", "load_tariff"),
                "source": "heuristic:load_tariff",
                "matched_pattern": "kw_value_heuristic",
                "region": "load_tariff",
            }

    if not results["tariff_category"]["value"]:
        tariff = infer_tariff(load_text or region_space["full_text"])
        if tariff:
            results["tariff_category"] = {
                "value": tariff,
                "confidence": score_field_confidence("tariff_category", tariff, "heuristic", "load_tariff"),
                "source": "heuristic:load_tariff",
                "matched_pattern": "tariff_token_heuristic",
                "region": "load_tariff",
            }

    if not results["meter_number"]["value"]:
        meter = infer_meter_number(region_space.get("meter_block", "") or region_space["full_text"], results["consumer_number"]["value"])
        if meter:
            meter = sanitize_value("meter_number", meter)
        if meter:
            results["meter_number"] = {
                "value": meter,
                "confidence": score_field_confidence("meter_number", meter, "heuristic", "meter_block"),
                "source": "heuristic:meter_block",
                "matched_pattern": "meter_digit_heuristic",
                "region": "meter_block",
            }

    previous, current, units = infer_reading_triplet(readings_text or region_space["full_text"])
    previous = sanitize_value("previous_reading", previous)
    current = sanitize_value("current_reading", current)
    units = sanitize_value("units_consumed", units)
    if not results["previous_reading"]["value"] and previous is not None:
        results["previous_reading"] = {
            "value": previous,
            "confidence": score_field_confidence("previous_reading", previous, "positional", "readings_block"),
            "source": "positional:readings_block",
            "matched_pattern": "reading_triplet_heuristic",
            "region": "readings_block",
        }
    if not results["current_reading"]["value"] and current is not None:
        results["current_reading"] = {
            "value": current,
            "confidence": score_field_confidence("current_reading", current, "positional", "readings_block"),
            "source": "positional:readings_block",
            "matched_pattern": "reading_triplet_heuristic",
            "region": "readings_block",
        }
    if not results["units_consumed"]["value"] and units is not None:
        results["units_consumed"] = {
            "value": units,
            "confidence": score_field_confidence("units_consumed", units, "positional", "readings_block"),
            "source": "positional:readings_block",
            "matched_pattern": "reading_diff_heuristic",
            "region": "readings_block",
        }

    return results
