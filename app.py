from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import APP_NAME, COMPANY_NAME, FIELD_LABELS, SUPPORTED_FILE_TYPES
from modules.excel_filler import build_solar_summary, fill_excel_template, generate_csv_output
from modules.extractor import BillExtractor
from modules.parser import parse_bill_data
from modules.utils import (
    append_history,
    clear_history,
    ensure_default_template,
    history_to_dataframe,
    image_to_preview,
    load_cell_mapping,
    save_uploaded_file,
    serialize_for_json,
    setup_logging,
    tail_log,
)
from modules.validator import validate_fields


st.set_page_config(
    page_title=APP_NAME,
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger = setup_logging()
ensure_default_template()
load_cell_mapping()

NUMERIC_FIELDS = {
    "bill_amount",
    "units_consumed",
    "connected_load_kw",
    "current_reading",
    "previous_reading",
}


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --page-bg-top: rgba(253, 198, 84, 0.16);
                --page-bg-right: rgba(77, 148, 255, 0.12);
                --page-base: #eef3f8;
                --surface: rgba(255, 255, 255, 0.96);
                --surface-strong: #ffffff;
                --surface-soft: #f8fbff;
                --border: rgba(148, 163, 184, 0.35);
                --text-main: #102a43;
                --text-muted: #486581;
                --sidebar-text: #f4f7fb;
                --sidebar-muted: #c9d6e2;
                --accent: #f59e0b;
                --accent-2: #f97316;
            }
            .stApp {
                background:
                    radial-gradient(circle at top left, var(--page-bg-top), transparent 28%),
                    radial-gradient(circle at top right, var(--page-bg-right), transparent 30%),
                    linear-gradient(180deg, rgba(248, 250, 252, 0.98), var(--page-base));
                color: var(--text-main);
            }
            [data-testid="stAppViewContainer"] {
                color: var(--text-main);
            }
            [data-testid="stAppViewContainer"] .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(9, 31, 52, 0.96), rgba(16, 55, 84, 0.98));
            }
            [data-testid="stSidebar"] * {
                color: var(--sidebar-text);
            }
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] p {
                color: var(--sidebar-muted) !important;
            }
            .hero-card {
                border-radius: 18px;
                padding: 1.2rem 1.4rem;
                margin-bottom: 1.2rem;
                background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 253, 0.96));
                border: 1px solid var(--border);
                box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
                backdrop-filter: blur(10px);
            }
            .hero-title {
                font-size: 2rem;
                font-weight: 700;
                color: #102a43;
                margin-bottom: 0.25rem;
            }
            .hero-subtitle {
                font-size: 1rem;
                color: var(--text-muted);
            }
            .metric-chip {
                display: inline-block;
                padding: 0.35rem 0.75rem;
                border-radius: 999px;
                margin-right: 0.5rem;
                background: rgba(255, 183, 77, 0.14);
                color: #7c4d00;
                font-size: 0.85rem;
                font-weight: 600;
            }
            .stButton>button, .stDownloadButton>button {
                border-radius: 12px;
                border: 0;
                background: linear-gradient(90deg, #f59e0b, #f97316);
                color: white;
                font-weight: 600;
            }
            .stButton>button:hover, .stDownloadButton>button:hover {
                filter: brightness(1.04);
            }
            h1, h2, h3, h4, h5, h6, p, label, div, span {
                color: inherit;
            }
            .section-title {
                margin: 1.1rem 0 0.55rem;
                padding: 0.8rem 1rem;
                border-radius: 14px;
                background: linear-gradient(180deg, var(--surface-strong), var(--surface-soft));
                border: 1px solid var(--border);
                color: var(--text-main);
                font-size: 1.05rem;
                font-weight: 700;
            }
            [data-testid="stFileUploader"],
            [data-testid="stExpander"],
            [data-testid="stDataFrame"],
            [data-testid="stTable"],
            [data-testid="stAlert"],
            [data-testid="stTextArea"],
            [data-testid="stCodeBlock"],
            .stSelectbox,
            .stMultiSelect,
            .stDateInput,
            .stTextInput,
            .stNumberInput {
                background: var(--surface);
                border-radius: 16px;
            }
            [data-testid="stFileUploader"] {
                padding: 0.35rem;
                border: 1px solid var(--border);
            }
            [data-testid="stExpander"] {
                border: 1px solid var(--border);
            }
            .stDataFrame, .stTable {
                border-radius: 14px;
                overflow: hidden;
                border: 1px solid var(--border);
                background: var(--surface-strong);
            }
            div[data-testid="stMarkdownContainer"] p {
                color: var(--text-main);
            }
            .stCaption {
                color: var(--text-muted) !important;
            }
            .st-emotion-cache-1r6slb0, .st-emotion-cache-16txtl3 {
                color: var(--text-main);
            }
            .stDataFrame, .stTable {
                border-radius: 14px;
                overflow: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    defaults = {
        "processed_records": [],
        "editable_data": {},
        "latest_output_path": None,
        "latest_csv_output_path": None,
        "latest_summary": None,
        "latest_preview_path": None,
        "latest_json": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## Energybae")
        st.caption("Solar analysis workflow automation")
        history_df = history_to_dataframe(limit=20)
        st.markdown("### Processing History")
        if history_df.empty:
            st.info("No processed bills yet.")
        else:
            st.dataframe(
                history_df[["timestamp", "file_name", "customer_name", "consumer_number", "status"]],
                width="stretch",
                hide_index=True,
            )
            if st.button("Delete Processing History", width="stretch"):
                clear_history()
                st.rerun()

        st.markdown("### Application Logs")
        st.code(tail_log(60), language="log")


def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-title">{APP_NAME}</div>
            <div class="hero-subtitle">Upload electricity bills, extract billing data, validate it, and generate a completed solar analysis Excel file for {COMPANY_NAME}.</div>
            <div style="margin-top:0.8rem;">
                <span class="metric-chip">OCR + Parsing</span>
                <span class="metric-chip">Excel Formula Safe</span>
                <span class="metric-chip">MSEDCL Oriented</span>
                <span class="metric-chip">Multi-Bill Ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def format_metric_value(value: float | None, prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    if value is None:
        return "Not available"
    formatted = f"{value:,.{decimals}f}"
    if decimals == 0:
        formatted = f"{value:,.0f}"
    return f"{prefix}{formatted}{suffix}"


def render_solar_report(summary: dict[str, float | None]) -> None:
    render_section_title("Solar Recommendation Report")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Suggested System Size",
            format_metric_value(summary.get("suggested_system_size_kw"), suffix=" kW"),
        )
    with col2:
        st.metric(
            "Estimated Monthly Savings",
            format_metric_value(summary.get("estimated_monthly_savings"), prefix="₹"),
        )
    with col3:
        st.metric(
            "Estimated Annual Savings",
            format_metric_value(summary.get("estimated_annual_savings"), prefix="₹"),
        )
    with col4:
        st.metric(
            "Estimated ROI",
            format_metric_value(summary.get("estimated_roi_years"), suffix=" years"),
        )

    detail_col_1, detail_col_2, detail_col_3 = st.columns(3)
    with detail_col_1:
        st.info(
            f"Monthly solar offset: {format_metric_value(summary.get('estimated_monthly_solar_offset_units'), suffix=' units')}"
        )
    with detail_col_2:
        st.info(
            f"Estimated system cost: {format_metric_value(summary.get('estimated_system_cost'), prefix='₹')}"
        )
    with detail_col_3:
        st.info(
            f"Bill rate used: {format_metric_value(summary.get('bill_per_unit'), prefix='₹', suffix='/unit')}"
        )


def process_single_file(uploaded_file, extractor: BillExtractor) -> dict:
    saved_path = save_uploaded_file(uploaded_file)
    extraction_result = extractor.process_file(saved_path)
    preview_path = None
    preview_image = extraction_result.get("preview_image")
    if preview_image is not None:
        preview_path = saved_path.with_suffix(".preview.png")
        preview_image.save(preview_path)

    return build_processed_record(
        file_name=uploaded_file.name,
        raw_text=extraction_result.get("text", ""),
        region_texts=extraction_result.get("region_texts", {}),
        extraction_method=extraction_result.get("method", "unknown"),
        ocr_engine=extraction_result.get("engine", "n/a"),
        ocr_confidence=extraction_result.get("ocr_confidence", 0.0),
        saved_path=str(saved_path),
        preview_path=str(preview_path) if preview_path else None,
    )


def build_processed_record(
    file_name: str,
    raw_text: str,
    region_texts: dict[str, str],
    extraction_method: str,
    ocr_engine: str,
    ocr_confidence: float,
    saved_path: str | None = None,
    preview_path: str | None = None,
) -> dict:
    parsed = parse_bill_data(raw_text, region_texts=region_texts)
    flattened = {field: info.get("value") for field, info in parsed.items()}
    confidence_map = {field: info.get("confidence", 0.0) for field, info in parsed.items()}
    source_map = {field: info.get("source", "unknown") for field, info in parsed.items()}
    validation = validate_fields(flattened)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "file_name": file_name,
        "saved_path": saved_path,
        "preview_path": preview_path,
        "raw_text": raw_text,
        "region_texts": region_texts,
        "extracted_data": flattened,
        "confidence_map": confidence_map,
        "source_map": source_map,
        "parsed_metadata": parsed,
        "ocr_confidence": ocr_confidence,
        "extraction_method": extraction_method,
        "ocr_engine": ocr_engine,
        "validation": validation,
        "status": "ready_for_review",
        "customer_name": flattened.get("customer_name"),
        "consumer_number": flattened.get("consumer_number"),
    }
    append_history(record)
    logger.info("Processed file %s with method %s", file_name, record["extraction_method"])
    return record


def process_pasted_text(raw_text: str) -> dict:
    return build_processed_record(
        file_name="pasted_bill_text.txt",
        raw_text=raw_text,
        region_texts={},
        extraction_method="pasted_text",
        ocr_engine="n/a",
        ocr_confidence=1.0,
        saved_path=None,
        preview_path=None,
    )


def build_editable_table(record: dict) -> pd.DataFrame:
    rows = []
    extracted_data = record["extracted_data"]
    confidence_map = record["confidence_map"]
    source_map = record.get("source_map", {})
    field_flags = record.get("validation", {}).get("field_flags", {})
    for field, label in FIELD_LABELS.items():
        rows.append(
            {
                "field_key": field,
                "Field": label,
                "Value": "" if extracted_data.get(field) is None else str(extracted_data.get(field)),
                "Confidence": round(float(confidence_map.get(field, 0.0)) * 100, 1),
                "Source": source_map.get(field, "unknown"),
                "Status": "Review" if field_flags.get(field) else "OK",
            }
        )
    return pd.DataFrame(rows)


def calculate_record_confidence(confidence_map: dict[str, float]) -> float:
    if not confidence_map:
        return 0.0
    scores = [score for score in confidence_map.values() if score > 0]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores) * 100, 1)


def normalize_editor_rows(edited_df: pd.DataFrame) -> dict[str, object]:
    final_data: dict[str, object] = {}
    for _, row in edited_df.iterrows():
        field_key = row["field_key"]
        value = row["Value"]
        if pd.isna(value):
            value = None
        elif isinstance(value, str):
            value = value.strip() or None

        if value is not None and field_key in NUMERIC_FIELDS:
            cleaned = str(value).replace(",", "")
            try:
                numeric_value = float(cleaned)
                value = int(numeric_value) if numeric_value.is_integer() else round(numeric_value, 2)
            except ValueError:
                pass

        final_data[field_key] = value
    return final_data


def main() -> None:
    inject_custom_css()
    initialize_session_state()
    render_sidebar()
    render_header()

    extractor = BillExtractor(logger=logger)

    render_section_title("Upload Bills")
    input_mode = st.radio(
        "Bill Input Method",
        ["Upload Bill File", "Paste Bill Text"],
        horizontal=True,
    )

    uploaded_files = []
    pasted_bill_text = ""
    if input_mode == "Upload Bill File":
        uploaded_files = st.file_uploader(
            "Upload one or more MSEDCL electricity bills",
            type=[file_type.lstrip(".") for file_type in SUPPORTED_FILE_TYPES],
            accept_multiple_files=True,
            help="Supported formats: PDF, JPG, JPEG, PNG",
        )
    else:
        pasted_bill_text = st.text_area(
            "Paste extracted bill text here",
            height=220,
            placeholder="Paste bill text content here if you want to process text directly instead of uploading a file.",
        )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        process_clicked = st.button(
            "Process Uploaded Bills" if input_mode == "Upload Bill File" else "Process Pasted Bill Text",
            width="stretch",
        )
    with col_b:
        clear_clicked = st.button("Clear Current Session", width="stretch")

    if clear_clicked:
        st.session_state.processed_records = []
        st.session_state.editable_data = {}
        st.session_state.latest_output_path = None
        st.session_state.latest_csv_output_path = None
        st.session_state.latest_summary = None
        st.session_state.latest_preview_path = None
        st.session_state.latest_json = None
        st.rerun()

    if process_clicked:
        if input_mode == "Upload Bill File":
            if not uploaded_files:
                st.warning("Upload at least one file before processing.")
            else:
                progress = st.progress(0, text="Starting bill processing...")
                records = []
                total = len(uploaded_files)
                for index, uploaded_file in enumerate(uploaded_files, start=1):
                    progress.progress(
                        int(((index - 1) / total) * 100),
                        text=f"Processing {uploaded_file.name} ({index}/{total})",
                    )
                    try:
                        record = process_single_file(uploaded_file, extractor)
                        records.append(record)
                    except Exception as exc:  # pragma: no cover
                        logger.exception("Failed processing %s", uploaded_file.name)
                        st.error(f"Failed to process {uploaded_file.name}: {exc}")
                progress.progress(100, text="Processing completed.")
                st.session_state.processed_records = records
        else:
            if not pasted_bill_text.strip():
                st.warning("Paste bill text before processing.")
            else:
                progress = st.progress(0, text="Starting bill processing...")
                try:
                    record = process_pasted_text(pasted_bill_text)
                    st.session_state.processed_records = [record]
                except Exception as exc:  # pragma: no cover
                    logger.exception("Failed processing pasted bill text")
                    st.error(f"Failed to process pasted bill text: {exc}")
                progress.progress(100, text="Processing completed.")

    if st.session_state.processed_records:
        render_section_title("Review Extracted Data")
        file_names = [record["file_name"] for record in st.session_state.processed_records]
        selected_name = st.selectbox("Select a processed bill", file_names)
        active_record = next(
            record for record in st.session_state.processed_records if record["file_name"] == selected_name
        )

        top_left, top_right = st.columns([1.15, 0.85])

        with top_left:
            st.subheader("Extracted Fields")
            st.caption(
                f"OCR confidence: {round(active_record['ocr_confidence'] * 100, 1)}% | "
                f"Method: {active_record['extraction_method']} | Engine: {active_record['ocr_engine']} | "
                f"Field confidence: {calculate_record_confidence(active_record['confidence_map'])}%"
            )
            editable_df = build_editable_table(active_record)
            edited_df = st.data_editor(
                editable_df,
                hide_index=True,
                width="stretch",
                disabled=["field_key", "Field", "Confidence", "Source", "Status"],
                key=f"editor_{selected_name}",
            )

        with top_right:
            st.subheader("Bill Preview")
            preview_path = active_record.get("preview_path")
            saved_path_value = active_record.get("saved_path")
            saved_path = Path(saved_path_value) if saved_path_value else None
            if preview_path and Path(preview_path).exists():
                st.image(str(preview_path), width="stretch")
            elif saved_path and saved_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                st.image(image_to_preview(saved_path), width="stretch")
            elif active_record["extraction_method"] == "pasted_text":
                st.info("Preview is not available for pasted bill text input.")
            else:
                st.info("Preview not available for this file in the current environment.")

        final_data = normalize_editor_rows(edited_df)
        validation = validate_fields(final_data)
        final_data = validation["normalized_data"]
        solar_summary = build_solar_summary(final_data)

        if solar_summary.get("suggested_system_size_kw") is not None:
            render_solar_report(solar_summary)

        with st.expander("Validation Summary", expanded=True):
            if validation["warnings"]:
                for warning in validation["warnings"]:
                    st.warning(warning)
            else:
                st.success("All key validations passed.")

        flagged_fields = {
            field: notes
            for field, notes in validation.get("field_flags", {}).items()
            if notes
        }
        if flagged_fields:
            with st.expander("Suspicious Fields", expanded=False):
                flag_rows = [
                    {
                        "Field": FIELD_LABELS.get(field, field),
                        "Issue": "; ".join(notes),
                    }
                    for field, notes in flagged_fields.items()
                ]
                st.dataframe(pd.DataFrame(flag_rows), width="stretch", hide_index=True)

        action_col_1, action_col_2, action_col_3 = st.columns([1, 1, 1])
        with action_col_1:
            generate_excel = st.button("Generate Excel Output", width="stretch")
        with action_col_2:
            st.download_button(
                "Download Extracted JSON",
                data=serialize_for_json(final_data),
                file_name=f"{Path(selected_name).stem}_extracted_data.json",
                mime="application/json",
                width="stretch",
            )
        with action_col_3:
            st.download_button(
                "Download Raw OCR Text",
                data=active_record["raw_text"],
                file_name=f"{Path(selected_name).stem}_raw_ocr.txt",
                mime="text/plain",
                width="stretch",
            )

        if generate_excel:
            if not validation["is_valid"]:
                st.error("Complete the required fields before generating the Excel output.")
            else:
                try:
                    output_path = fill_excel_template(final_data, selected_name)
                    csv_output_path = generate_csv_output(final_data, selected_name)
                    st.session_state.latest_output_path = str(output_path)
                    st.session_state.latest_csv_output_path = str(csv_output_path)
                    st.session_state.latest_summary = solar_summary
                    st.session_state.latest_json = final_data
                    active_record["status"] = "excel_generated"
                    append_history(
                        {
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                            "file_name": selected_name,
                            "customer_name": final_data.get("customer_name"),
                            "consumer_number": final_data.get("consumer_number"),
                            "status": "excel_generated",
                            "output_path": str(output_path),
                            "csv_output_path": str(csv_output_path),
                        }
                    )
                    logger.info(
                        "Generated Excel and CSV outputs for %s at %s and %s",
                        selected_name,
                        output_path.name,
                        csv_output_path.name,
                    )
                    st.success("Excel and CSV files generated successfully.")
                except Exception as exc:  # pragma: no cover
                    logger.exception("Excel generation failed for %s", selected_name)
                    st.error(f"File generation failed: {exc}")

        if st.session_state.latest_output_path and Path(st.session_state.latest_output_path).exists():
            with open(st.session_state.latest_output_path, "rb") as output_file:
                st.download_button(
                    "Download Completed Excel",
                    data=output_file.read(),
                    file_name=Path(st.session_state.latest_output_path).name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )

        if st.session_state.latest_csv_output_path and Path(st.session_state.latest_csv_output_path).exists():
            with open(st.session_state.latest_csv_output_path, "rb") as output_file:
                st.download_button(
                    "Download Completed CSV",
                    data=output_file.read(),
                    file_name=Path(st.session_state.latest_csv_output_path).name,
                    mime="text/csv",
                    width="stretch",
                )

        with st.expander("Structured JSON Preview"):
            st.json(json.loads(serialize_for_json(final_data)))

        with st.expander("Confidence Diagnostics"):
            diagnostics = []
            parsed_metadata = active_record.get("parsed_metadata", {})
            for field, label in FIELD_LABELS.items():
                info = parsed_metadata.get(field, {})
                diagnostics.append(
                    {
                        "Field": label,
                        "Value": "" if info.get("value") is None else str(info.get("value")),
                        "Confidence %": round(float(info.get("confidence", 0.0)) * 100, 1),
                        "Source": info.get("source"),
                        "Region": info.get("region"),
                        "Pattern": "" if info.get("matched_pattern") is None else str(info.get("matched_pattern")),
                    }
                )
            st.dataframe(pd.DataFrame(diagnostics), width="stretch", hide_index=True)

        region_texts = active_record.get("region_texts", {})
        if region_texts:
            with st.expander("Region OCR Output"):
                for region_name, region_text in region_texts.items():
                    if region_text.strip():
                        st.markdown(f"**{region_name.replace('_', ' ').title()}**")
                        st.code(region_text, language="text")

        with st.expander("Raw OCR / Extracted Text"):
            st.text_area(
                "OCR content",
                active_record["raw_text"],
                height=220,
                label_visibility="collapsed",
            )


if __name__ == "__main__":
    main()
