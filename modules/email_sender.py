"""
Email Sender Module for automated report dispatch.
Allows sending generated Excel/PDF reports via SMTP.
"""

from __future__ import annotations

import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any


# Email configuration defaults (can be overridden via environment variables)
DEFAULT_SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
DEFAULT_SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
DEFAULT_SMTP_USER = os.environ.get("SMTP_USER", "")
DEFAULT_SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
DEFAULT_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Solar Load Calculator")
DEFAULT_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"


class EmailSender:
    """Email sender with SMTP support."""
    
    def __init__(
        self,
        smtp_host: str = DEFAULT_SMTP_HOST,
        smtp_port: int = DEFAULT_SMTP_PORT,
        smtp_user: str = DEFAULT_SMTP_USER,
        smtp_password: str = DEFAULT_SMTP_PASSWORD,
        use_tls: bool = DEFAULT_USE_TLS,
        from_name: str = DEFAULT_FROM_NAME,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_name = from_name
    
    def is_configured(self) -> bool:
        """Check if email sender is properly configured."""
        return bool(self.smtp_user and self.smtp_password)
    
    def validate_email(self, email: str) -> bool:
        """Validate email address format."""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Plain text email body
            attachments: List of file paths to attach
            html_body: Optional HTML version of the body
        
        Returns:
            Dictionary with 'success' boolean and 'message' string
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "Email sender not configured. Please set SMTP_USER and SMTP_PASSWORD environment variables.",
            }
        
        if not self.validate_email(to_email):
            return {
                "success": False,
                "message": f"Invalid recipient email address: {to_email}",
            }
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.smtp_user}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Attach plain text body
            msg.attach(MIMEText(body, "plain"))
            
            # Attach HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Attach files
            for file_path in attachments or []:
                if not file_path.exists():
                    continue
                
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {file_path.name}",
                )
                msg.attach(part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "SMTP authentication failed. Please check SMTP credentials.",
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "message": f"SMTP error: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
            }
    
    def send_solar_report(
        self,
        to_email: str,
        customer_name: str | None,
        excel_path: Path | None = None,
        pdf_path: Path | None = None,
        bill_data: dict[str, Any] | None = None,
        solar_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a solar analysis report via email.
        
        Args:
            to_email: Recipient email address
            customer_name: Customer name for personalization
            excel_path: Path to Excel report
            pdf_path: Path to PDF proposal
            bill_data: Extracted bill data for the email body
            solar_summary: Solar calculation summary
        
        Returns:
            Dictionary with 'success' boolean and 'message' string
        """
        subject = f"Solar Analysis Report - {customer_name or 'Customer'}"
        
        # Build plain text body
        body_lines = [
            f"Dear {customer_name or 'Customer'},",
            "",
            "Please find attached your solar energy analysis report.",
            "",
        ]
        
        if bill_data:
            body_lines.extend([
                "Bill Summary:",
                f"  - Billing Month: {bill_data.get('billing_month', 'N/A')}",
                f"  - Units Consumed: {bill_data.get('units_consumed', 'N/A')}",
                f"  - Bill Amount: ₹{bill_data.get('bill_amount', 'N/A')}",
                "",
            ])
        
        if solar_summary:
            body_lines.extend([
                "Solar Recommendation:",
                f"  - Suggested System Size: {solar_summary.get('suggested_system_size_kw', 'N/A')} kW",
                f"  - Estimated Monthly Savings: ₹{solar_summary.get('estimated_monthly_savings', 'N/A')}",
                f"  - Estimated Annual Savings: ₹{solar_summary.get('estimated_annual_savings', 'N/A')}",
                f"  - Estimated ROI: {solar_summary.get('estimated_roi_years', 'N/A')} years",
                "",
            ])
        
        body_lines.extend([
            "Please review the attached reports for detailed analysis.",
            "",
            "Best regards,",
            "Solar Load Calculator Team",
        ])
        
        body = "\n".join(body_lines)
        
        # Build HTML body
        html_lines = [
            "<html>",
            "<body>",
            f"<p>Dear {customer_name or 'Customer'},</p>",
            "<p>Please find attached your solar energy analysis report.</p>",
        ]
        
        if bill_data:
            html_lines.extend([
                "<h3>Bill Summary</h3>",
                "<ul>",
                f"<li>Billing Month: {bill_data.get('billing_month', 'N/A')}</li>",
                f"<li>Units Consumed: {bill_data.get('units_consumed', 'N/A')}</li>",
                f"<li>Bill Amount: ₹{bill_data.get('bill_amount', 'N/A')}</li>",
                "</ul>",
            ])
        
        if solar_summary:
            html_lines.extend([
                "<h3>Solar Recommendation</h3>",
                "<ul>",
                f"<li>Suggested System Size: {solar_summary.get('suggested_system_size_kw', 'N/A')} kW</li>",
                f"<li>Estimated Monthly Savings: ₹{solar_summary.get('estimated_monthly_savings', 'N/A')}</li>",
                f"<li>Estimated Annual Savings: ₹{solar_summary.get('estimated_annual_savings', 'N/A')}</li>",
                f"<li>Estimated ROI: {solar_summary.get('estimated_roi_years', 'N/A')} years</li>",
                "</ul>",
            ])
        
        html_lines.extend([
            "<p>Please review the attached reports for detailed analysis.</p>",
            "<p>Best regards,<br>Solar Load Calculator Team</p>",
            "</body>",
            "</html>",
        ])
        
        html_body = "\n".join(html_lines)
        
        # Collect attachments
        attachments = []
        if excel_path and excel_path.exists():
            attachments.append(excel_path)
        if pdf_path and pdf_path.exists():
            attachments.append(pdf_path)
        
        return self.send_email(to_email, subject, body, attachments, html_body)


def create_email_sender(
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
) -> EmailSender:
    """
    Create an EmailSender with optional overrides.
    
    Environment variables take precedence over parameters.
    """
    return EmailSender(
        smtp_host=smtp_host or DEFAULT_SMTP_HOST,
        smtp_port=smtp_port or DEFAULT_SMTP_PORT,
        smtp_user=smtp_user or DEFAULT_SMTP_USER,
        smtp_password=smtp_password or DEFAULT_SMTP_PASSWORD,
    )


def send_test_email(
    to_email: str,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
) -> dict[str, Any]:
    """
    Send a test email to verify SMTP configuration.
    
    Returns:
        Dictionary with 'success' boolean and 'message' string
    """
    sender = create_email_sender(smtp_host, smtp_port, smtp_user, smtp_password)
    
    return sender.send_email(
        to_email=to_email,
        subject="Test Email - Solar Load Calculator",
        body="This is a test email to verify your SMTP configuration is working correctly.",
    )
