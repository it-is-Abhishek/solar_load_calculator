from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from modules.utils import create_output_copy, ensure_default_template, load_cell_mapping


def generate_output_filename(source_name: str) -> str:
    stem = Path(source_name).stem.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}_solar_analysis_{timestamp}.xlsx"


def fill_excel_template(
    extracted_data: dict[str, Any],
    source_name: str,
    template_path: Path | None = None,
) -> Path:
    template_path = template_path or ensure_default_template()
    mapping = load_cell_mapping()
    output_path = create_output_copy(template_path, generate_output_filename(source_name))

    workbook = load_workbook(output_path)
    sheet = workbook.active

    for field, cell in mapping.items():
        if field not in extracted_data:
            continue
        sheet[cell] = extracted_data[field]

    workbook.save(output_path)
    return output_path
