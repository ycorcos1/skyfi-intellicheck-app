"""
Export service responsible for generating JSON and PDF company reports.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.models.analysis import CompanyAnalysis
from app.models.company import Company

logger = logging.getLogger(__name__)

_PRIMARY_YELLOW = "#FFCC00"
_SUCCESS_GREEN = "#28A745"
_DANGER_RED = "#DC3545"
_WARNING_ORANGE = "#FF8800"
_NEUTRAL_GRAY = "#888888"


def _safe_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Return ISO timestamp string in UTC if a datetime is provided."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _ensure_font_loaded(font_name: str, font_file: str) -> None:
    """Register a TrueType font if it is not already available."""
    if font_name in pdfmetrics.getRegisteredFontNames():
        return
    try:
        pdfmetrics.registerFont(TTFont(font_name, font_file))
    except Exception:  # pylint: disable=broad-exception-caught
        # Font is optional; fall back to defaults if not found.
        logger.debug("Font %s could not be registered; using default fonts.", font_name)


def generate_json_report(
    company: Company,
    latest_analysis: Optional[CompanyAnalysis],
) -> Dict[str, Any]:
    """
    Generate structured JSON report that mirrors the PRD specification.

    Args:
        company: Company SQLAlchemy model instance.
        latest_analysis: Most recent CompanyAnalysis instance or None.

    Returns:
        Dictionary representing the export payload.
    """
    report: Dict[str, Any] = {
        "company": {
            "id": str(company.id),
            "name": company.name,
            "domain": company.domain,
            "website_url": company.website_url,
            "email": company.email,
            "phone": company.phone,
            "status": company.status.value,
            "risk_score": company.risk_score,
            "analysis_status": company.analysis_status.value,
            "current_step": company.current_step,
            "created_at": _safe_datetime(company.created_at),
            "updated_at": _safe_datetime(company.updated_at),
            "last_analyzed_at": _safe_datetime(company.last_analyzed_at),
        },
        "analysis": None,
    }

    if latest_analysis:
        report["analysis"] = {
            "id": str(latest_analysis.id),
            "version": latest_analysis.version,
            "algorithm_version": latest_analysis.algorithm_version,
            "risk_score": latest_analysis.risk_score,
            "is_complete": latest_analysis.is_complete,
            "failed_checks": latest_analysis.failed_checks or [],
            "submitted_data": latest_analysis.submitted_data or {},
            "discovered_data": latest_analysis.discovered_data or {},
            "signals": latest_analysis.signals or [],
            "llm_summary": latest_analysis.llm_summary,
            "llm_details": latest_analysis.llm_details,
            "created_at": _safe_datetime(latest_analysis.created_at),
        }

    logger.info(
        "Generated JSON export for company %s (analysis_version=%s)",
        company.id,
        latest_analysis.version if latest_analysis else None,
    )

    return report


def generate_pdf_report(
    company: Company,
    latest_analysis: Optional[CompanyAnalysis],
) -> bytes:
    """
    Generate a PDF report following the design spec.

    Args:
        company: Company SQLAlchemy model instance.
        latest_analysis: Most recent CompanyAnalysis instance or None.

    Returns:
        Binary PDF data.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=54,
    )

    _ensure_font_loaded("BricolageGrotesque-Regular", "fonts/BricolageGrotesque-Regular.ttf")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=1,
        fontSize=28,
        textColor=colors.black,
        spaceAfter=24,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Heading2"],
        alignment=1,
        fontSize=16,
        textColor=colors.black,
        spaceAfter=32,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=12,
    )
    badge_style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        alignment=1,
        fontSize=16,
        textColor=colors.white,
        backColor=_PRIMARY_YELLOW,
        borderPadding=12,
        leading=20,
    )

    story: list[Any] = []

    # Cover
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("SkyFi IntelliCheck", title_style))
    story.append(Paragraph("Verification Report", subtitle_style))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"<b>{company.name}</b>", styles["Heading3"]))
    story.append(Paragraph(f"Domain: {company.domain}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    if latest_analysis:
        risk_score = latest_analysis.risk_score
        badge_color, badge_label = _risk_visuals(risk_score)
        badge_style_clone = ParagraphStyle(
            "BadgeClone",
            parent=badge_style,
            backColor=badge_color,
        )
        story.append(
            Paragraph(
                f"RISK SCORE: {risk_score}<br/><b>{badge_label}</b>",
                badge_style_clone,
            )
        )
    else:
        info_style = ParagraphStyle(
            "InfoBadge",
            parent=badge_style,
            backColor=_NEUTRAL_GRAY,
        )
        story.append(Paragraph("Analysis Pending", info_style))

    story.append(Spacer(1, 0.5 * inch))
    story.append(
        Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        )
    )
    story.append(PageBreak())

    # Company Overview
    story.append(Paragraph("Company Overview", heading_style))
    overview_rows = [
        ["Field", "Value"],
        ["Name", company.name],
        ["Domain", company.domain],
        ["Website", company.website_url or "N/A"],
        ["Email", company.email or "N/A"],
        ["Phone", company.phone or "N/A"],
        ["Status", company.status.value.title()],
        ["Risk Score", str(company.risk_score)],
        ["Created", company.created_at.strftime("%Y-%m-%d") if company.created_at else "N/A"],
        ["Last Analyzed", company.last_analyzed_at.strftime("%Y-%m-%d") if company.last_analyzed_at else "Pending"],
    ]
    overview_table = Table(overview_rows, colWidths=[2.2 * inch, 3.8 * inch])
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]
        )
    )
    story.append(overview_table)
    story.append(Spacer(1, 0.3 * inch))

    if not latest_analysis:
        story.append(
            Paragraph(
                "This company has not completed an automated verification yet. "
                "JSON export is still available but analysis content is pending.",
                styles["Normal"],
            )
        )
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info("Generated PDF export for company %s without analysis.", company.id)
        return pdf_bytes

    # Submitted vs Discovered
    story.append(Paragraph("Submitted vs Discovered Data", heading_style))
    comparison_rows = [["Field", "Submitted", "Discovered"]]
    submitted_data = latest_analysis.submitted_data or {}
    discovered_data = latest_analysis.discovered_data or {}
    all_keys = sorted(set(submitted_data.keys()) | set(discovered_data.keys()))
    for key in all_keys:
        submitted_value = submitted_data.get(key, "N/A")
        discovered_value = discovered_data.get(key, "N/A")
        comparison_rows.append(
            [
                key.replace("_", " ").title(),
                _stringify_value(submitted_value),
                _stringify_value(discovered_value),
            ]
        )

    comparison_table = Table(comparison_rows, colWidths=[2 * inch, 2.25 * inch, 2.25 * inch])
    comparison_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(comparison_table)
    story.append(Spacer(1, 0.3 * inch))

    # Signals
    story.append(Paragraph("Verification Signals", heading_style))
    signals = latest_analysis.signals or []
    if signals:
        signal_rows = [["Field", "Value", "Status"]]
        for signal in signals:
            signal_rows.append(
                [
                    _stringify_value(signal.get("field", "N/A")).replace("_", " ").title(),
                    _stringify_value(signal.get("value", "N/A")),
                    signal.get("status", "unknown").upper(),
                ]
            )
        signal_table = Table(signal_rows, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        signal_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(signal_table)
    else:
        story.append(Paragraph("No verification signals were recorded.", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # LLM summary
    story.append(Paragraph("AI Narrative Summary", heading_style))
    summary_text = latest_analysis.llm_summary or "No AI summary available."
    summary_style = ParagraphStyle(
        "Summary",
        parent=styles["Normal"],
        backColor=colors.lightgrey,
        borderPadding=10,
        leading=16,
    )
    story.append(Paragraph(summary_text, summary_style))
    story.append(Spacer(1, 0.3 * inch))

    # Detailed Appendix
    story.append(PageBreak())
    story.append(Paragraph("Detailed Appendix", heading_style))
    details_text = latest_analysis.llm_details or "No additional AI details were provided."
    story.append(Paragraph(details_text, styles["Normal"]))
    story.append(Spacer(1, 0.4 * inch))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(
        Paragraph(
            f"Version: {latest_analysis.version} | "
            f"Algorithm: {latest_analysis.algorithm_version} | "
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info(
        "Generated PDF export for company %s (analysis_version=%s, bytes=%s)",
        company.id,
        latest_analysis.version,
        len(pdf_bytes),
    )
    return pdf_bytes


def fetch_company_with_analysis(
    db: Session,
    company_id,
    version: Optional[int] = None,
) -> tuple[Optional[Company], Optional[CompanyAnalysis]]:
    """
    Helper to fetch a company and either a specific analysis version or the latest analysis.

    Args:
        db: SQLAlchemy session.
        company_id: UUID of the company.
        version: Optional analysis version to retrieve. If omitted, the latest analysis is returned.

    Returns:
        Tuple of (Company or None, CompanyAnalysis or None).
    """
    company: Optional[Company] = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )

    if company is None:
        return None, None

    analysis_query = db.query(CompanyAnalysis).filter(CompanyAnalysis.company_id == company_id)

    if version is not None:
        analysis = analysis_query.filter(CompanyAnalysis.version == version).first()
    else:
        analysis = analysis_query.order_by(CompanyAnalysis.version.desc()).first()

    return company, analysis


def _risk_visuals(score: int) -> tuple[str, str]:
    """Return color hex and label for a risk score."""
    if score < 30:
        return _SUCCESS_GREEN, "Low Risk"
    if score < 70:
        return _WARNING_ORANGE, "Moderate Risk"
    return _DANGER_RED, "High Risk"


def _stringify_value(value: Any) -> str:
    """Convert complex values into displayable strings."""
    if value is None:
        return "N/A"
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)
    return str(value)


