from pathlib import Path
import json
from modules.extractor import BillExtractor
from modules.utils import setup_logging

logger = setup_logging()
extractor = BillExtractor(logger=logger)

file_path = Path("/Users/abhishek/Desktop/solar_load_calculator/uploads/20260501_121847_303546_Copy_of_WhatsApp_Image_2026-02-12_at_13.48.47_(1).jpeg")
extraction_result = extractor.process_file(file_path)

with open("ocr_dump.json", "w") as f:
    json.dump({
        "raw_text": extraction_result.get("text", ""),
        "region_texts": extraction_result.get("region_texts", {})
    }, f, indent=2)
print("Dumped OCR to ocr_dump.json")
fields = {k: v["value"] for k, v in extraction_result["parsed_data"].items()}
print(json.dumps(fields, indent=2))
