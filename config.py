from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODULES_DIR = BASE_DIR / "modules"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"
HISTORY_FILE = LOGS_DIR / "processing_history.jsonl"
APP_LOG_FILE = LOGS_DIR / "app.log"

APP_NAME = "Solar Load Calculator Automation"
COMPANY_NAME = "Energybae"

SUPPORTED_IMAGE_TYPES = [".png", ".jpg", ".jpeg"]
SUPPORTED_FILE_TYPES = [".pdf", ".png", ".jpg", ".jpeg"]

DEFAULT_TEMPLATE_PATH = TEMPLATES_DIR / "solar_template.xlsx"
CELL_MAPPING_PATH = TEMPLATES_DIR / "cell_mapping.json"

OCR_ENGINE_PRIORITY = ["easyocr", "tesseract"]
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

REQUIRED_FIELDS = [
    "customer_name",
    "consumer_number",
    "billing_month",
    "bill_amount",
    "units_consumed",
]

FIELD_LABELS = {
    "customer_name": "Customer Name",
    "consumer_number": "Consumer Number",
    "billing_month": "Billing Month",
    "bill_amount": "Bill Amount",
    "units_consumed": "Units Consumed",
    "connected_load_kw": "Connected Load (kW)",
    "tariff_category": "Tariff Category",
    "meter_number": "Meter Number",
    "due_date": "Due Date",
    "current_reading": "Current Reading",
    "previous_reading": "Previous Reading",
}

DEFAULT_FIELD_MAPPING = {
    "customer_name": "B3",
    "consumer_number": "B4",
    "billing_month": "B5",
    "bill_amount": "B6",
    "units_consumed": "B7",
    "connected_load_kw": "B8",
    "tariff_category": "B9",
    "meter_number": "B10",
    "due_date": "B11",
    "current_reading": "B12",
    "previous_reading": "B13",
}
