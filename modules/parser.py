from __future__ import annotations

import re
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


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x0c", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_first_match(
    text: str,
    patterns: list[str],
    transform=None,
    flags: int = re.IGNORECASE,
) -> tuple[Any, str | None]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=flags)
        if match:
            value = match.group(1).strip(" :.-")
            if transform:
                value = transform(value)
            return value, pattern
    return None, None


def clean_currency(value: str) -> float | None:
    value = value.replace(",", "").replace("Rs.", "").replace("INR", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group()) if match else None


def clean_number(value: str) -> float | int | None:
    value = value.replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None
    number = float(match.group())
    return int(number) if number.is_integer() else round(number, 2)


def clean_text(value: str) -> str:
    return re.sub(r"\s{2,}", " ", value).strip()


def fuzzy_match_month(token: str) -> str | None:
    month_map = {
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
    cleaned = re.sub(r"[^a-z]", "", token.lower())
    if len(cleaned) < 3:
        return None
    best = None
    best_score = 0.0
    for key, value in month_map.items():
        score = SequenceMatcher(None, cleaned[:3], key).ratio()
        if score > best_score:
            best = value
            best_score = score
    return best if best_score >= 0.55 else None


def extract_month_from_text(raw_text: str) -> str | None:
    for token in re.findall(r"[A-Za-z]{3,12}[-/ ]?\d{2,4}", raw_text):
        month = fuzzy_match_month(token)
        year_match = re.search(r"(\d{4})", token)
        if month and year_match:
            return f"{month}-{year_match.group(1)}"

    valid_years = re.findall(r"(20\d{2})", raw_text)
    fallback_year = valid_years[0] if valid_years else None
    for line in raw_text.splitlines():
        if "month" not in line.lower():
            continue
        year_match = re.search(r"(20\d{2})", line)
        target_year = year_match.group(1) if year_match else fallback_year
        if not target_year:
            continue
        for token in re.findall(r"[A-Za-z]{3,12}", line):
            month = fuzzy_match_month(token)
            if month:
                return f"{month}-{target_year}"
    return None


def extract_fallback_consumer_number(raw_text: str) -> str | None:
    candidates = re.findall(r"\b\d{10,13}\b", raw_text)
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda value: (len(value), candidates.count(value)), reverse=True)
    return ranked[0]


def extract_fallback_meter_number(raw_text: str, consumer_number: str | None) -> str | None:
    lines = raw_text.splitlines()
    for line in lines:
        if "meter" in line.lower():
            match = re.search(r"\b\d{8,12}\b", line)
            if match:
                return match.group(0)
    candidates = [value for value in re.findall(r"\b\d{8,12}\b", raw_text) if value != consumer_number]
    return candidates[-1] if candidates else None


def extract_fallback_customer_name(raw_text: str) -> str | None:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    excluded_tokens = {"MSEDCL", "GSTIN", "BILL", "SUPPLY", "MONTH", "ENERGY", "BANK"}
    best_line = None
    for line in lines[:12]:
        clean_line = re.sub(r"[^A-Za-z\s]", " ", line)
        words = [word for word in clean_line.split() if len(word) > 2]
        if len(words) < 2:
            continue
        uppercase_ratio = sum(1 for word in words if word.upper() == word) / max(len(words), 1)
        if uppercase_ratio < 0.5:
            continue
        if any(word in excluded_tokens for word in words):
            continue
        if re.search(r"\d", line):
            continue
        if best_line is None or len(words) > len(best_line.split()):
            best_line = " ".join(words)
    if best_line:
        return best_line

    phrase_matches = re.findall(r"\b[A-Z]{3,}(?:\s+[A-Z]{3,}){1,4}\b", raw_text)
    phrase_matches = [
        match for match in phrase_matches
        if not any(token in excluded_tokens for token in match.split())
    ]
    if phrase_matches:
        return max(phrase_matches, key=len)
    return None


def extract_fallback_tariff(raw_text: str) -> str | None:
    line_match = re.search(r"\b(?:LT|HT)[\s\-]*[A-Z0-9]*\s*(?:Res|Residential|Comm|Commercial)?\b", raw_text, re.IGNORECASE)
    if not line_match:
        return None
    value = line_match.group(0).replace("90LT", "LT").replace("0LT", "LT")
    value = re.sub(r"\s+", " ", value).strip(" -")
    if "res" in value.lower() and "residential" not in value.lower():
        value = value.replace("Res", "Residential")
    return value.upper().replace("RESIDENTIAL", "Residential").replace("LT", "LT")


def extract_fallback_dates(raw_text: str) -> list[str]:
    raw_text = raw_text.replace("+", "-")
    dates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", raw_text)
    seen = []
    for date in dates:
        parts = re.split(r"[/-]", date)
        day, month, year = map(int, parts)
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2035):
            continue
        if date not in seen:
            seen.append(date)
    return seen


def extract_fallback_amount(raw_text: str) -> float | None:
    amounts = []
    for match in re.findall(r"\b\d{3,6}[.,]\d{2}\b", raw_text):
        value = clean_currency(match.replace(",", ".") if match.count(",") == 1 and "." not in match else match)
        if value and value > 100:
            amounts.append(value)
    if amounts:
        return max(amounts)

    int_amounts = []
    for match in re.findall(r"\b\d{3,5}\b", raw_text):
        value = int(match)
        if 100 <= value <= 100000:
            int_amounts.append(value)
    return max(int_amounts) if int_amounts else None


def infer_readings_and_units(raw_text: str) -> tuple[int | None, int | None, int | None]:
    number_candidates = [int(value) for value in re.findall(r"\b\d{4,6}\b", raw_text)]
    reading_candidates = [value for value in number_candidates if 5000 <= value <= 99999 and not (2020 <= value <= 2035)]
    current = None
    previous = None
    units = None
    if len(reading_candidates) >= 2:
        current = max(reading_candidates)
        previous_candidates = [value for value in reading_candidates if value < current]
        previous = max(previous_candidates) if previous_candidates else min(reading_candidates)
        if current > previous:
            diff = current - previous
            if 1 <= diff <= 5000:
                units = diff

    unit_matches = [int(value) for value in re.findall(r"\b\d{2,4}\b", raw_text)]
    plausible_units = [value for value in unit_matches if 10 <= value <= 2500 and not (2020 <= value <= 2035)]
    if plausible_units:
        frequent = max(set(plausible_units), key=plausible_units.count)
        if units is None or plausible_units.count(frequent) > 1:
            units = frequent
    return current, previous, units


def score_field_confidence(
    field: str,
    value: Any,
    source: str,
    raw_text: str,
) -> float:
    if value in (None, ""):
        return 0.0

    base_scores = {
        "line_regex": 0.94,
        "fallback_regex": 0.78,
        "heuristic": 0.58,
    }
    score = base_scores.get(source, 0.5)
    field_type = FIELD_TYPES.get(field, "text")

    if field_type == "currency":
        if isinstance(value, (int, float)) and value > 0:
            score += 0.03
    elif field_type == "numeric":
        if isinstance(value, (int, float)) and value >= 0:
            score += 0.03
        if field == "connected_load_kw" and isinstance(value, (int, float)) and 0 < value <= 50:
            score += 0.02
        if field == "units_consumed" and isinstance(value, (int, float)) and 0 < value <= 100000:
            score += 0.02
    elif field_type == "id":
        digits_only = re.sub(r"\D", "", str(value))
        if len(digits_only) >= 8:
            score += 0.04
    elif field_type == "date":
        if re.fullmatch(r"\d{2}[/-]\d{2}[/-]\d{2,4}", str(value)):
            score += 0.04
    elif field_type == "text":
        clean_value = str(value).strip()
        if len(clean_value) >= 4:
            score += 0.02
        if field == "customer_name" and clean_value.upper() == clean_value:
            score += 0.02

    raw_lower = raw_text.lower()
    label_hints = {
        "customer_name": ["consumer name", "customer name", "name of consumer"],
        "consumer_number": ["consumer no", "consumer number", "consumer id"],
        "billing_month": ["billing month", "bill month", "month"],
        "bill_amount": ["bill amount", "amount payable", "net amount"],
        "units_consumed": ["units consumed", "energy consumed", "consumption"],
        "connected_load_kw": ["connected load", "sanctioned load"],
        "tariff_category": ["tariff", "tariff category", "category"],
        "meter_number": ["meter no", "meter number"],
        "due_date": ["due date", "payment due date"],
        "current_reading": ["current reading", "present reading"],
        "previous_reading": ["previous reading", "past reading"],
    }
    if any(label in raw_lower for label in label_hints.get(field, [])):
        score += 0.02

    if field == "tariff_category" and len(str(value)) > 30:
        score -= 0.08
    if field == "customer_name" and any(char.isdigit() for char in str(value)):
        score -= 0.1
    if field in {"consumer_number", "meter_number"} and len(str(value)) < 5:
        score -= 0.15

    return round(max(0.0, min(score, 0.99)), 3)


def parse_bill_data(raw_text: str) -> dict[str, dict[str, Any]]:
    text = normalize_whitespace(raw_text)
    text_multiline = raw_text

    line_patterns = {
        "customer_name": [
            r"^(?:consumer name|name of consumer|customer name)\s*[:\-]?\s*([^\n\r]+)$",
            r"^(?:name)\s*[:\-]?\s*([^\n\r]+)$",
        ],
        "consumer_number": [
            r"^(?:consumer no|consumer number|consumer id|service no)\s*[:\-]?\s*([0-9]{8,15})$",
            r"^(?:consumer no\.)\s*([0-9]{8,15})$",
        ],
        "billing_month": [
            r"^(?:billing month|bill month|month)\s*[:\-]?\s*([^\n\r]+)$",
            r"^(?:bill date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})$",
        ],
        "bill_amount": [
            r"^(?:current bill amount|bill amount|net amount|total current bill)\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9,]+(?:\.\d{1,2})?)$",
            r"^(?:amount payable)\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9,]+(?:\.\d{1,2})?)$",
        ],
        "units_consumed": [
            r"^(?:units consumed|consumption \(units\)|energy consumed|current month units)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)$",
            r"^(?:total units)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)$",
        ],
        "connected_load_kw": [
            r"^(?:connected load|sanctioned load)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)\s*(?:kw|kva)?$",
        ],
        "tariff_category": [
            r"^(?:tariff category|tariff|category)\s*[:\-]?\s*([^\n\r]+)$",
        ],
        "meter_number": [
            r"^(?:meter no|meter number)\s*[:\-]?\s*([A-Za-z0-9\-]{5,20})$",
        ],
        "due_date": [
            r"^(?:due date|payment due date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})$",
        ],
        "current_reading": [
            r"^(?:current reading|present reading)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)$",
        ],
        "previous_reading": [
            r"^(?:previous reading|past reading)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)$",
        ],
    }

    fallback_patterns = {
        "customer_name": [
            r"(?:consumer name|name of consumer|customer name)\s*[:\-]?\s*([A-Z][A-Z\s\.]{2,})",
        ],
        "consumer_number": [
            r"(?:consumer no|consumer number|consumer id|service no)\s*[:\-]?\s*([0-9]{8,15})",
        ],
        "billing_month": [
            r"(?:billing month|bill month|month)\s*[:\-]?\s*([A-Za-z]{3,9}\s*[-/]\s*\d{2,4})",
            r"(?:bill date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})",
        ],
        "bill_amount": [
            r"(?:current bill amount|bill amount|net amount|total current bill)\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9,]+(?:\.\d{1,2})?)",
            r"(?:amount payable)\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9,]+(?:\.\d{1,2})?)",
        ],
        "units_consumed": [
            r"(?:units consumed|consumption \(units\)|energy consumed|current month units)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
        ],
        "connected_load_kw": [
            r"(?:connected load|sanctioned load)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)\s*(?:kw|kva)?",
        ],
        "tariff_category": [
            r"(?:tariff category)\s*[:\-]?\s*([A-Za-z0-9\-\s\/]{3,40})",
        ],
        "meter_number": [
            r"(?:meter no|meter number)\s*[:\-]?\s*([A-Za-z0-9\-]{5,20})",
        ],
        "due_date": [
            r"(?:due date|payment due date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})",
        ],
        "current_reading": [
            r"(?:current reading|present reading)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
        ],
        "previous_reading": [
            r"(?:previous reading|past reading)\s*[:\-]?\s*([0-9,]+(?:\.\d{1,2})?)",
        ],
    }

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

    results: dict[str, dict[str, Any]] = {}
    for field, field_patterns in line_patterns.items():
        value, pattern = extract_first_match(
            text_multiline,
            field_patterns,
            transform=transformers.get(field),
            flags=re.IGNORECASE | re.MULTILINE,
        )
        source = "line_regex"
        if value is None:
            value, pattern = extract_first_match(
                text,
                fallback_patterns.get(field, []),
                transform=transformers.get(field),
            )
            source = "fallback_regex"
        confidence = score_field_confidence(field, value, source, raw_text)
        results[field] = {
            "value": value,
            "confidence": confidence,
            "source": source,
            "matched_pattern": pattern,
        }

    if not results["customer_name"]["value"]:
        fallback_name = extract_fallback_customer_name(text_multiline)
        if fallback_name:
            results["customer_name"] = {
                "value": clean_text(fallback_name),
                "confidence": score_field_confidence(
                    "customer_name",
                    fallback_name,
                    "heuristic",
                    raw_text,
                ),
                "source": "heuristic",
                "matched_pattern": "uppercase_line_heuristic",
            }

    if not results["consumer_number"]["value"]:
        fallback_consumer = extract_fallback_consumer_number(text_multiline)
        if fallback_consumer:
            results["consumer_number"] = {
                "value": fallback_consumer,
                "confidence": score_field_confidence("consumer_number", fallback_consumer, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "digit_sequence_heuristic",
            }

    if not results["billing_month"]["value"]:
        fallback_month = extract_month_from_text(text_multiline)
        if fallback_month:
            results["billing_month"] = {
                "value": fallback_month,
                "confidence": score_field_confidence("billing_month", fallback_month, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "month_token_heuristic",
            }

    if not results["tariff_category"]["value"]:
        fallback_tariff = extract_fallback_tariff(text_multiline)
        if fallback_tariff:
            results["tariff_category"] = {
                "value": fallback_tariff,
                "confidence": score_field_confidence("tariff_category", fallback_tariff, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "tariff_token_heuristic",
            }

    if not results["meter_number"]["value"]:
        fallback_meter = extract_fallback_meter_number(
            text_multiline,
            results["consumer_number"]["value"],
        )
        if fallback_meter:
            results["meter_number"] = {
                "value": fallback_meter,
                "confidence": score_field_confidence("meter_number", fallback_meter, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "meter_digit_heuristic",
            }

    if not results["bill_amount"]["value"]:
        fallback_amount = extract_fallback_amount(text_multiline)
        if fallback_amount:
            results["bill_amount"] = {
                "value": fallback_amount,
                "confidence": score_field_confidence("bill_amount", fallback_amount, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "amount_heuristic",
            }

    fallback_dates = extract_fallback_dates(text_multiline)
    if not results["due_date"]["value"] and fallback_dates:
        results["due_date"] = {
            "value": fallback_dates[-1],
            "confidence": score_field_confidence("due_date", fallback_dates[-1], "heuristic", raw_text),
            "source": "heuristic",
            "matched_pattern": "date_list_heuristic",
        }

    if not results["connected_load_kw"]["value"]:
        kw_match = re.search(r"\b(\d{1,2}(?:\.\d{1,2})?)\s*kw\b", text_multiline, re.IGNORECASE)
        if kw_match:
            kw_value = clean_number(kw_match.group(1))
            results["connected_load_kw"] = {
                "value": kw_value,
                "confidence": score_field_confidence("connected_load_kw", kw_value, "heuristic", raw_text),
                "source": "heuristic",
                "matched_pattern": "kw_token_heuristic",
            }

    current_reading, previous_reading, inferred_units = infer_readings_and_units(text_multiline)
    if not results["current_reading"]["value"] and current_reading is not None:
        results["current_reading"] = {
            "value": current_reading,
            "confidence": score_field_confidence("current_reading", current_reading, "heuristic", raw_text),
            "source": "heuristic",
            "matched_pattern": "reading_sequence_heuristic",
        }
    if not results["previous_reading"]["value"] and previous_reading is not None:
        results["previous_reading"] = {
            "value": previous_reading,
            "confidence": score_field_confidence("previous_reading", previous_reading, "heuristic", raw_text),
            "source": "heuristic",
            "matched_pattern": "reading_sequence_heuristic",
        }
    if not results["units_consumed"]["value"] and inferred_units is not None:
        results["units_consumed"] = {
            "value": inferred_units,
            "confidence": score_field_confidence("units_consumed", inferred_units, "heuristic", raw_text),
            "source": "heuristic",
            "matched_pattern": "unit_inference_heuristic",
        }

    return results
