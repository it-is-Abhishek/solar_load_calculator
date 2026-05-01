"""
PDF Generator Module for Solar Recommendations
Generates professional PDF proposals combining extracted bill data, ROI calculations, and visualizations.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

try:
    from fpdf import FPDF
    _FPDF_AVAILABLE = True
except ImportError:
    FPDF = object  # use plain object as base so class definition doesn't fail
    _FPDF_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    MATPLOTLIB_AVAILABLE = False
    plt = None
    np = None


class SolarProposalPDF(FPDF):
    """Custom PDF class for solar proposal documents."""
    
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
    
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(9, 55, 99)
        self.cell(0, 10, "Solar Energy Proposal", ln=True, align="C")
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    
    def add_chapter_title(self, title: str):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(33, 33, 33)
        self.cell(0, 10, title, ln=True)
        self.ln(2)
    
    def add_chapter_body(self, body: str):
        self.set_font("helvetica", "", 11)
        self.set_text_color(66, 66, 66)
        self.multi_cell(0, 6, body)
        self.ln(4)
    
    def add_field_row(self, label: str, value: str):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(33, 33, 33)
        self.cell(50, 7, label, border=0)
        self.set_font("helvetica", "", 10)
        self.set_text_color(66, 66, 66)
        self.cell(0, 7, str(value), ln=True, border=0)
    
    def add_separator(self):
        self.ln(3)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)


def generate_bar_chart(
    monthly_savings: list[float],
    months: list[str],
    output_path: Path,
) -> str | None:
    """Generate a bar chart visualization for monthly savings."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        x_pos = np.arange(len(months))
        ax.bar(x_pos, monthly_savings, color="#FF9800", edgecolor="#E65100", alpha=0.8)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Monthly Savings (₹)", fontsize=10)
        ax.set_xlabel("Month", fontsize=10)
        ax.set_title("Estimated Monthly Savings After Solar Installation", fontsize=12, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, format="png", transparent=False)
        plt.close(fig)
        return str(output_path)
    except Exception:  # pragma: no cover
        return None


def generate_savings_chart(
    annual_savings: float,
    system_cost: float,
    roi_years: float,
    output_path: Path,
) -> str | None:
    """Generate a cumulative savings chart over system lifetime."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    try:
        years = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        cumulative_savings = [annual_savings * year for year in years]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(years, cumulative_savings, marker="o", linewidth=2, color="#4CAF50", label="Cumulative Savings")
        ax.axhline(y=system_cost, color="#F44336", linestyle="--", linewidth=1.5, label=f"System Cost: ₹{system_cost:,.0f}")
        ax.axvline(x=roi_years, color="#2196F3", linestyle=":", linewidth=1.5, label=f"ROI: {roi_years:.1f} years")
        
        ax.set_xlabel("Years", fontsize=10)
        ax.set_ylabel("Cumulative Savings (₹)", fontsize=10)
        ax.set_title("Solar Investment Payback Timeline", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left")
        ax.grid(linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, format="png", transparent=False)
        plt.close(fig)
        return str(output_path)
    except Exception:  # pragma: no cover
        return None


def format_currency(value: float | None, prefix: str = "₹") -> str:
    """Format a numeric value as currency string."""
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


def format_kw(value: float | None) -> str:
    """Format a kW value."""
    if value is None:
        return "N/A"
    return f"{value:.2f} kW"


def generate_solar_proposal(
    bill_data: dict[str, Any],
    solar_summary: dict[str, Any],
    customer_name: str | None = None,
    output_dir: Path | None = None,
) -> Path | None:
    """
    Generate a comprehensive PDF solar proposal.
    
    Args:
        bill_data: Extracted bill data dictionary
        solar_summary: Solar calculation summary dictionary
        customer_name: Optional customer name for the proposal
        output_dir: Directory to save the PDF (defaults to ./outputs)
    
    Returns:
        Path to the generated PDF file, or None if generation failed
    """
    if not _FPDF_AVAILABLE:
        return None
    
    if output_dir is None:
        output_dir = Path("./outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"solar_proposal_{timestamp}.pdf"
    output_path = output_dir / file_name
    
    pdf = SolarProposalPDF()
    
    # Title section
    pdf.add_chapter_title("Solar Energy Proposal")
    
    # Customer Information
    pdf.add_chapter_title("Customer Information")
    pdf.add_field_row("Customer Name:", customer_name or bill_data.get("customer_name", "N/A"))
    pdf.add_field_row("Consumer Number:", bill_data.get("consumer_number", "N/A"))
    pdf.add_field_row("Billing Month:", bill_data.get("billing_month", "N/A"))
    pdf.add_separator()
    
    # Current Energy Summary
    pdf.add_chapter_title("Current Energy Usage")
    pdf.add_field_row("Monthly Units:", bill_data.get("units_consumed", "N/A"))
    pdf.add_field_row("Current Bill Amount:", format_currency(bill_data.get("bill_amount")))
    pdf.add_field_row("Connected Load:", format_kw(bill_data.get("connected_load_kw")))
    pdf.add_field_row("Tariff Category:", bill_data.get("tariff_category", "N/A"))
    pdf.add_separator()
    
    # Solar Recommendation
    pdf.add_chapter_title("Solar Recommendation")
    pdf.add_field_row("Suggested System Size:", format_kw(solar_summary.get("suggested_system_size_kw")))
    pdf.add_field_row("Estimated System Cost:", format_currency(solar_summary.get("estimated_system_cost")))
    pdf.add_field_row("Cost per kW:", format_currency(solar_summary.get("bill_per_unit"), suffix="/unit"))
    pdf.add_separator()
    
    # Financial Benefits
    pdf.add_chapter_title("Estimated Financial Benefits")
    pdf.add_field_row("Monthly Solar Offset:", f"{solar_summary.get('estimated_monthly_solar_offset_units', 'N/A')} units")
    pdf.add_field_row("Monthly Savings:", format_currency(solar_summary.get("estimated_monthly_savings")))
    pdf.add_field_row("Annual Savings:", format_currency(solar_summary.get("estimated_annual_savings")))
    pdf.add_field_row("Estimated ROI:", f"{solar_summary.get('estimated_roi_years', 'N/A')} years")
    pdf.add_separator()
    
    # Add charts if matplotlib is available
    if MATPLOTLIB_AVAILABLE and solar_summary.get("estimated_annual_savings"):
        charts_dir = output_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate monthly savings bar chart
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        annual_savings = solar_summary.get("estimated_annual_savings", 0)
        monthly_avg = annual_savings / 12
        monthly_savings = [monthly_avg * (1.1 if m >= 4 and m <= 9 else 0.9) for m in range(12)]  # Summer bias
        
        bar_chart_path = charts_dir / f"monthly_savings_{timestamp}.png"
        chart_result = generate_bar_chart(monthly_savings, months, bar_chart_path)
        
        if chart_result:
            pdf.add_page()
            pdf.add_chapter_title("Monthly Savings Visualization")
            pdf.image(str(bar_chart_path), x=10, w=190)
            pdf.ln(5)
        
        # Generate cumulative savings chart
        system_cost = solar_summary.get("estimated_system_cost", 0)
        roi_years = solar_summary.get("estimated_roi_years", 10)
        
        savings_chart_path = charts_dir / f"cumulative_savings_{timestamp}.png"
        savings_result = generate_savings_chart(annual_savings, system_cost, roi_years, savings_chart_path)
        
        if savings_result:
            pdf.add_page()
            pdf.add_chapter_title("Investment Payback Timeline")
            pdf.image(str(savings_chart_path), x=10, w=190)
            pdf.ln(5)
    
    # Terms and disclaimers
    pdf.add_page()
    pdf.add_chapter_title("Terms & Disclaimers")
    pdf.add_chapter_body(
        "1. This proposal is based on the current electricity bill data and is an estimate only.\n"
        "2. Actual solar system performance depends on sunlight hours, panel orientation, and weather conditions.\n"
        "3. Government subsidies and incentives are not included and may vary by region.\n"
        "4. Please consult with a certified solar installer for a detailed site assessment.\n"
        "5. This document is for informational purposes only and does not constitute a binding offer."
    )
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(
        0,
        10,
        f"Generated on {datetime.datetime.now().strftime('%d-%m-%Y at %H:%M:%S')} by Solar Load Calculator",
        ln=True,
    )
    
    try:
        pdf.output(str(output_path))
        return output_path
    except Exception:  # pragma: no cover
        return None


def generate_invoice_pdf(
    bill_data: dict[str, Any],
    output_dir: Path | None = None,
) -> Path | None:
    """Generate a simple invoice PDF for the electricity bill."""
    if not _FPDF_AVAILABLE:
        return None
    
    if output_dir is None:
        output_dir = Path("./outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"bill_invoice_{timestamp}.pdf"
    output_path = output_dir / file_name
    
    pdf = SolarProposalPDF()
    
    # Invoice header
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(9, 55, 99)
    pdf.cell(0, 12, "Electricity Bill Invoice", ln=True, align="C")
    pdf.ln(8)
    
    # Customer details
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 8, "Bill To:", ln=True)
    pdf.ln(2)
    
    pdf.add_field_row("Name:", bill_data.get("customer_name", "N/A"))
    pdf.add_field_row("Consumer Number:", bill_data.get("consumer_number", "N/A"))
    pdf.add_field_row("Billing Period:", bill_data.get("billing_month", "N/A"))
    pdf.add_separator()
    
    # Bill summary
    pdf.add_chapter_title("Bill Summary")
    pdf.add_field_row("Units Consumed:", str(bill_data.get("units_consumed", "N/A")))
    pdf.add_field_row("Amount Payable:", format_currency(bill_data.get("bill_amount")))
    pdf.add_field_row("Due Date:", bill_data.get("due_date", "N/A"))
    pdf.add_separator()
    
    # Payment details
    pdf.add_chapter_title("Payment Details")
    pdf.add_field_row("Meter Number:", bill_data.get("meter_number", "N/A"))
    pdf.add_field_row("Connected Load:", format_kw(bill_data.get("connected_load_kw")))
    pdf.add_field_row("Tariff:", bill_data.get("tariff_category", "N/A"))
    
    try:
        pdf.output(str(output_path))
        return output_path
    except Exception:  # pragma: no cover
        return None
