from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from config import REQUIRED_FIELDS


def normalize_field_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return value


def validate_fields(data: dict[str, Any]) -> dict[str, Any]:
    normalized_data = {
        field: normalize_field_value(value)
        for field, value in data.items()
    }
    warnings: list[str] = []
    field_flags: dict[str, list[str]] = {field: [] for field in normalized_data}

    missing_fields = [field for field in REQUIRED_FIELDS if not normalized_data.get(field)]
    if missing_fields:
        warnings.append(
            "Missing required fields: " + ", ".join(field.replace("_", " ") for field in missing_fields)
        )
        for field in missing_fields:
            field_flags.setdefault(field, []).append("Missing required value")

    numeric_fields = [
        "bill_amount",
        "units_consumed",
        "connected_load_kw",
        "current_reading",
        "previous_reading",
    ]
    for field in numeric_fields:
        value = normalized_data.get(field)
        if value in (None, ""):
            continue
        try:
            normalized_data[field] = float(value)
        except (TypeError, ValueError):
            warnings.append(f"{field.replace('_', ' ').title()} should be numeric.")
            field_flags.setdefault(field, []).append("Expected numeric value")

    load_kw = _to_float(normalized_data.get("connected_load_kw"))
    if load_kw is not None and not (0.5 <= load_kw <= 5):
        warnings.append("Connected load looks suspicious for a residential MSEDCL bill.")
        field_flags.setdefault("connected_load_kw", []).append("Outside expected residential range 0.5–5 kW")

    units = _to_float(normalized_data.get("units_consumed"))
    if units is not None and not (10 <= units <= 2500):
        warnings.append("Units consumed looks suspicious.")
        field_flags.setdefault("units_consumed", []).append("Outside expected monthly range")

    bill_amount = _to_float(normalized_data.get("bill_amount"))
    if bill_amount is not None and not (150 <= bill_amount <= 50000):
        warnings.append("Bill amount looks suspicious.")
        field_flags.setdefault("bill_amount", []).append("Outside expected bill amount range")

    prev_read = _to_float(normalized_data.get("previous_reading"))
    curr_read = _to_float(normalized_data.get("current_reading"))
    if prev_read is not None and curr_read is not None:
        if curr_read < prev_read:
            warnings.append("Current reading is lower than previous reading.")
            field_flags.setdefault("current_reading", []).append("Lower than previous reading")
        else:
            diff = curr_read - prev_read
            if units is not None and abs(diff - units) > 10:
                warnings.append("Units consumed does not match the reading difference closely.")
                field_flags.setdefault("units_consumed", []).append("Reading difference mismatch")
                field_flags.setdefault("current_reading", []).append("Reading difference mismatch")
                field_flags.setdefault("previous_reading", []).append("Reading difference mismatch")

    due_date = normalized_data.get("due_date")
    if isinstance(due_date, str):
        parsed = _parse_date(due_date)
        if parsed is None:
            warnings.append("Due date is not a valid date.")
            field_flags.setdefault("due_date", []).append("Invalid date format")
        elif parsed.year > datetime.now().year + 1:
            warnings.append("Due date year is unrealistic.")
            field_flags.setdefault("due_date", []).append("Unrealistic year")

    for field in ["consumer_number", "meter_number"]:
        value = normalized_data.get(field)
        digits = "".join(char for char in str(value or "") if char.isdigit())
        if len(digits) == 10 and digits.startswith(("7", "8", "9")):
            warnings.append(f"{field.replace('_', ' ').title()} looks like a phone number and should be reviewed.")
            field_flags.setdefault(field, []).append("Looks like a phone number")

    return {
        "is_valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "field_flags": field_flags,
        "normalized_data": normalized_data,
    }


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
