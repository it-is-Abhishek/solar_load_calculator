from typing import Any

from config import DEFAULT_SOLAR_COST_PER_KW


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def estimate_bill_rate(units: float) -> float:
    """Estimate a realistic per-unit rate based on MSEDCL slabs, excluding fixed charges/arrears."""
    if units <= 100:
        return 6.0
    elif units <= 300:
        return 8.5
    elif units <= 500:
        return 11.5
    else:
        return 13.5


def build_solar_summary(extracted_data: dict[str, Any]) -> dict[str, float | None]:
    units = _to_float(extracted_data.get("units_consumed"))
    load_kw = _to_float(extracted_data.get("connected_load_kw"))
    bill_amount = _to_float(extracted_data.get("bill_amount"))

    bill_per_unit = estimate_bill_rate(units) if units and units > 0 else None

    # In Maharashtra, 1 kW solar generates ~120 units/month on average
    estimated_monthly_solar_offset_units = round(units * 0.90, 2) if units is not None else None

    suggested_system_size_kw = None
    if units is not None:
        derived_size = round(units / 120, 2)
        suggested_system_size_kw = round(max(0.5, derived_size), 2)
    elif load_kw is not None and 0.5 <= load_kw <= 5.0:
        suggested_system_size_kw = round(load_kw, 2)

    estimated_monthly_savings = None
    if estimated_monthly_solar_offset_units is not None and bill_per_unit is not None:
        savings = estimated_monthly_solar_offset_units * bill_per_unit
        if bill_amount is not None:
            savings = min(savings, bill_amount * 0.95)  # Can't save more than the bill minus fixed charges
        estimated_monthly_savings = round(savings, 2)

    estimated_annual_savings = (
        round(estimated_monthly_savings * 12, 2)
        if estimated_monthly_savings is not None
        else None
    )

    estimated_system_cost = (
        round(suggested_system_size_kw * DEFAULT_SOLAR_COST_PER_KW, 2)
        if suggested_system_size_kw is not None
        else None
    )

    estimated_roi_years = None
    if estimated_system_cost and estimated_annual_savings and estimated_annual_savings > 0:
        estimated_roi_years = round(estimated_system_cost / estimated_annual_savings, 2)

    return {
        "bill_per_unit": bill_per_unit,
        "estimated_monthly_solar_offset_units": estimated_monthly_solar_offset_units,
        "suggested_system_size_kw": suggested_system_size_kw,
        "estimated_monthly_savings": estimated_monthly_savings,
        "estimated_annual_savings": estimated_annual_savings,
        "estimated_system_cost": estimated_system_cost,
        "estimated_roi_years": estimated_roi_years,
    }
