# Solar Load Calculator Automation

An AI-powered Streamlit web application for **Energybae** that automates:

**Electricity Bill Upload -> OCR/Data Extraction -> Validation -> Excel Template Population -> Downloadable Solar Analysis Excel**

The app is optimized for **MSEDCL-style Maharashtra electricity bills** and is designed as a clean, modular MVP that is easy to explain in an internship interview.

## Features

- Upload electricity bills in `PDF`, `JPG`, `JPEG`, or `PNG`
- Paste bill text directly for quick processing when OCR text is already available
- Extract text from:
  - Embedded PDF text using `pdfplumber`
  - OCR from images and scanned PDFs using `EasyOCR` or `Tesseract`
- Preprocess bill images with `OpenCV` for better OCR quality
- Parse important fields using regex and heuristics
- Review and manually correct extracted values before export
- Validate required and numeric fields
- Fill only mapped input cells in an Excel template using `openpyxl`
- Preserve all formulas by writing into a copied template output
- Download:
  - Completed Excel file
  - Extracted JSON
  - Raw OCR text
- Processing history and live log panel
- Supports multiple bill uploads in one session

## Project Structure

```text
solar_load_calculator/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
│
├── modules/
│   ├── __init__.py
│   ├── extractor.py
│   ├── parser.py
│   ├── excel_filler.py
│   ├── validator.py
│   ├── preprocess.py
│   └── utils.py
│
├── templates/
│   ├── solar_template.xlsx
│   └── cell_mapping.json
│
├── uploads/
├── outputs/
└── logs/
```

## Architecture Flow

1. User uploads one or more electricity bills, or pastes bill text directly.
2. Files are stored in the `uploads/` folder.
3. The extractor:
   - reads embedded PDF text if available
   - otherwise runs OCR on scanned PDFs or images
4. The parser extracts billing fields using regex + simple heuristics.
   - each field receives its own confidence score based on match strength and value plausibility
5. The UI displays extracted fields in an editable table.
6. The validator flags missing or suspicious fields.
7. The Excel filler copies the template and writes only mapped cells.
8. The completed Excel file is saved in `outputs/` and becomes downloadable.

## Extracted Fields

The parser targets these fields:

- Customer Name
- Consumer Number
- Billing Month
- Bill Amount
- Units Consumed
- Connected Load (kW)
- Tariff Category
- Meter Number
- Due Date
- Current Reading
- Previous Reading

## Excel Safety

- The app **never edits the original template**
- A copy of `templates/solar_template.xlsx` is created in `outputs/`
- Only cells defined in `templates/cell_mapping.json` are updated
- Existing formulas in the template remain untouched

## Installation

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install OCR engine dependencies

#### Option A: Tesseract

Install Tesseract on your machine and make sure it is available in PATH.

macOS:

```bash
brew install tesseract
```

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### Option B: EasyOCR

`EasyOCR` is already included in `requirements.txt`. It can work without a system Tesseract install, but it may take longer to install because of deep learning dependencies.

## Run the App

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal.

## Local Deployment Notes

- This project is deployment-friendly for a local laptop or internship demo machine.
- For best OCR quality, use clear bill scans or high-resolution photos.
- If `EasyOCR` is unavailable, the app falls back to `Tesseract`.
- If a PDF already contains embedded text, OCR is skipped for faster processing.

## Configuration

### `config.py`

Contains:

- directory paths
- required fields
- label mapping
- default template path
- default Excel field mapping

### `templates/cell_mapping.json`

This file controls which extracted field goes into which Excel cell.

Example:

```json
{
  "customer_name": "B3",
  "consumer_number": "B4",
  "billing_month": "B5"
}
```

You can change this mapping without modifying the app logic.

## MSEDCL Optimization

The parsing logic is tuned toward common MSEDCL-style labels such as:

- `Consumer No`
- `Bill Amount`
- `Units Consumed`
- `Connected Load`
- `Meter No`
- `Due Date`

Because bill layouts can vary, the app includes:

- regex extraction
- fallback heuristics
- field-level confidence scoring
- editable review before final export

This combination gives practical real-world reliability for an MVP.

## Logging and History

- Logs are stored in `logs/app.log`
- Processing history is stored in `logs/processing_history.jsonl`
- The sidebar shows recent runs and recent logs

## Interview Explanation Summary

If you need to explain the project quickly:

- `app.py` handles the frontend and workflow orchestration
- `extractor.py` handles PDF/image OCR extraction
- `preprocess.py` improves image quality before OCR
- `parser.py` converts raw text into structured bill data
- `parser.py` also assigns field-wise confidence using line matches, fallback matches, and plausibility checks
- `validator.py` checks missing fields and suspicious values
- `excel_filler.py` writes validated data into a copied Excel template
- `utils.py` manages logging, file handling, history, and template setup

## Future Improvements

- field-level ML extraction using LLM structured outputs
- better multi-page PDF handling
- template management for multiple DISCOM formats
- SQLite database for persistent history
- authentication and user-wise dashboards
- batch ZIP export for multiple generated Excel files

## Run Commands

```bash
pip install -r requirements.txt
streamlit run app.py
```
# solar_load_calculator
