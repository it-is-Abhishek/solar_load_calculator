from __future__ import annotations

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
    missing_fields = [field for field in REQUIRED_FIELDS if not normalized_data.get(field)]
    if missing_fields:
        warnings.append(
            "Missing required fields: " + ", ".join(field.replace("_", " ") for field in missing_fields)
        )

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
            float(value)
        except (TypeError, ValueError):
            warnings.append(f"{field.replace('_', ' ').title()} should be numeric.")

    prev_read = normalized_data.get("previous_reading")
    curr_read = normalized_data.get("current_reading")
    try:
        if prev_read not in (None, "") and curr_read not in (None, ""):
            if float(curr_read) < float(prev_read):
                warnings.append("Current reading is lower than previous reading.")
    except (TypeError, ValueError):
        pass

    return {
        "is_valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "normalized_data": normalized_data,
    }
