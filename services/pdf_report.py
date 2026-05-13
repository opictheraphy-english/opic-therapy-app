"""Eric No branded PDF export (reportlab). Safe import: module loads without reportlab."""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

_cached_pdf_ok: Optional[bool] = None


def pdf_export_available() -> bool:
    """True if reportlab can be imported (cached). Does not build a PDF."""
    global _cached_pdf_ok
    if _cached_pdf_ok is not None:
        return _cached_pdf_ok
    try:
        import reportlab  # noqa: F401

        _cached_pdf_ok = True
    except ImportError:
        _cached_pdf_ok = False
    return bool(_cached_pdf_ok)


def _ascii_safe(text: str) -> str:
    return "".join(c if ord(c) < 128 else "?" for c in (text or ""))


def build_exam_pdf(
    aggregates: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    patient_label: str = "OPIc Therapy Candidate",
) -> Optional[bytes]:
    """
    Build PDF bytes, or None if reportlab is missing or generation fails.
    All reportlab imports are inside this function (lazy).
    """
    if not pdf_export_available():
        logger.info("PDF export skipped: reportlab not installed")
        return None

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        logger.warning("reportlab import failed inside build_exam_pdf: %s", e)
        return None

    navy = colors.HexColor("#0f172a")
    soft_line = colors.HexColor("#e2e8f0")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="EricTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=navy,
        alignment=TA_CENTER,
        spaceAfter=12,
        leading=26,
    )
    sub_style = ParagraphStyle(
        name="EricSub",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    h2 = ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=navy,
        spaceBefore=14,
        spaceAfter=8,
    )
    body = ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=10, leading=14)

    story = []
    story.append(Paragraph("ERIC NO · OPIc PRECISION LAB", sub_style))
    story.append(Paragraph("Comprehensive Speech Assessment Report", title_style))
    story.append(
        Paragraph(
            f"<i>{patient_label}</i><br/>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sub_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    ov = aggregates.get("overall_display", "—")
    conf = aggregates.get("confidence", "—")
    story.append(Paragraph("Overall Predicted Level", h2))
    story.append(
        Paragraph(
            f"<b><font size=18 color='#0f172a'>{ov} (Estimated)</font></b><br/>"
            f"Confidence: <b>{conf}%</b><br/>{aggregates.get('confidence_note', '')}",
            body,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Session Summary Statistics", h2))
    story.append(
        Paragraph(
            f"Avg WPM: <b>{aggregates.get('avg_wpm')}</b> &nbsp;|&nbsp; "
            f"Avg sentences (units): <b>{aggregates.get('avg_sentence_count')}</b> &nbsp;|&nbsp; "
            f"Avg semantic density: <b>{aggregates.get('avg_semantic_density')}</b><br/>"
            f"Strongest topic: <b>{aggregates.get('strongest_topic')}</b> &nbsp;|&nbsp; "
            f"Weakest topic: <b>{aggregates.get('weakest_topic')}</b>",
            body,
        )
    )
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Question Summary", h2))
    if summary_rows:
        hdr = list(summary_rows[0].keys())
        data = [hdr] + [[str(row.get(k, "")) for k in hdr] for row in summary_rows]
        t = Table(data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), navy),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, soft_line),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Per-Question Records", h2))
    for row in items:
        qid = row.get("q_id")
        res = row.get("result") or {}
        tx_raw = (res.get("transcript") or "")[:1200]
        tx = escape(_ascii_safe(tx_raw)) if tx_raw else "(no transcript)"
        story.append(
            Paragraph(
                f"<b>Q{qid}</b> · {_ascii_safe(str(row.get('topic', '')))} · <i>{_ascii_safe(str(row.get('type', '')))}</i><br/>"
                f"<font size=9>{tx}</font>",
                body,
            )
        )
        story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "<i>This report is generated for self-study purposes and does not replace "
            "an official OPIc score.</i>",
            ParagraphStyle(name="Foot", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        )
    )

    try:
        doc.build(story)
        data = buf.getvalue()
        return data
    except Exception as e:
        logger.exception("PDF build failed: %s", e)
        return None
    finally:
        buf.close()
