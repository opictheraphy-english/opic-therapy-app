"""Eric No branded PDF export (reportlab). Safe import: module loads without reportlab."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

_cached_pdf_ok: Optional[bool] = None
_font_regular_name: str = "Helvetica"
_font_bold_name: str = "Helvetica-Bold"
_fonts_registered: bool = False

_FONT_REGULAR_FILE = "NotoSansKR-Regular.ttf"
_FONT_BOLD_FILE = "NotoSansKR-Bold.ttf"
_FONT_FAMILY = "NotoSansKR"


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


def _font_paths() -> Tuple[str, str]:
    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
    )
    return (
        os.path.join(base, _FONT_REGULAR_FILE),
        os.path.join(base, _FONT_BOLD_FILE),
    )


def _register_pdf_fonts() -> Tuple[str, str]:
    """Register Noto Sans KR once; fall back to Helvetica if files are missing."""
    global _fonts_registered, _font_regular_name, _font_bold_name
    if _fonts_registered:
        return _font_regular_name, _font_bold_name

    regular_path, bold_path = _font_paths()
    if not os.path.isfile(regular_path):
        try:
            logger.warning("[PDF_FONT] missing path=%s", regular_path)
        except Exception:
            pass
        _fonts_registered = True
        return _font_regular_name, _font_bold_name
    if not os.path.isfile(bold_path):
        try:
            logger.warning("[PDF_FONT] missing path=%s", bold_path)
        except Exception:
            pass
        _fonts_registered = True
        return _font_regular_name, _font_bold_name

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        from reportlab.pdfbase.ttfonts import TTFont

        if _FONT_FAMILY not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(_FONT_FAMILY, regular_path))
        bold_name = f"{_FONT_FAMILY}-Bold"
        if bold_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
        registerFontFamily(
            _FONT_FAMILY,
            normal=_FONT_FAMILY,
            bold=bold_name,
        )
        _font_regular_name = _FONT_FAMILY
        _font_bold_name = bold_name
    except Exception as exc:
        try:
            logger.warning("[PDF_FONT] register failed: %s", exc)
        except Exception:
            pass

    _fonts_registered = True
    return _font_regular_name, _font_bold_name


def _pdf_plain(text: Any) -> str:
    """Strip control chars; keep Korean and other Unicode for plain table cells."""
    raw = str(text or "")
    return "".join(ch for ch in raw if ch >= " " or ch in "\t\n\r")


def _pdf_text(text: Any) -> str:
    """Minimal sanitize + XML escape for Paragraph markup."""
    return escape(_pdf_plain(text))


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

    font_regular, font_bold = _register_pdf_fonts()

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
        fontName=font_bold,
        fontSize=22,
        textColor=navy,
        alignment=TA_CENTER,
        spaceAfter=12,
        leading=26,
    )
    sub_style = ParagraphStyle(
        name="EricSub",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    h2 = ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=14,
        textColor=navy,
        spaceBefore=14,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=10,
        leading=14,
    )

    story = []
    story.append(Paragraph("ERIC NO · OPIc PRECISION LAB", sub_style))
    story.append(Paragraph("Comprehensive Speech Assessment Report", title_style))
    story.append(
        Paragraph(
            f"<i>{_pdf_text(patient_label)}</i><br/>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sub_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    ov = aggregates.get("overall_display", "—")
    conf = aggregates.get("confidence", "—")
    conf_note = _pdf_text(aggregates.get("confidence_note", ""))
    story.append(Paragraph("Overall Predicted Level", h2))
    story.append(
        Paragraph(
            f"<b><font size=18 color='#0f172a'>{_pdf_text(ov)} (Estimated)</font></b><br/>"
            f"Confidence: <b>{_pdf_text(conf)}%</b><br/>{conf_note}",
            body,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Session Summary Statistics", h2))
    story.append(
        Paragraph(
            f"Avg WPM: <b>{_pdf_text(aggregates.get('avg_wpm'))}</b> &nbsp;|&nbsp; "
            f"Avg sentences (units): <b>{_pdf_text(aggregates.get('avg_sentence_count'))}</b> &nbsp;|&nbsp; "
            f"Avg semantic density: <b>{_pdf_text(aggregates.get('avg_semantic_density'))}</b><br/>"
            f"Strongest topic: <b>{_pdf_text(aggregates.get('strongest_topic'))}</b> &nbsp;|&nbsp; "
            f"Weakest topic: <b>{_pdf_text(aggregates.get('weakest_topic'))}</b>",
            body,
        )
    )
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Question Summary", h2))
    if summary_rows:
        hdr = list(summary_rows[0].keys())
        data = [hdr] + [[_pdf_plain(row.get(k, "")) for k in hdr] for row in summary_rows]
        t = Table(data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), navy),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font_bold),
                    ("FONTNAME", (0, 1), (-1, -1), font_regular),
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
    from utils.text_utils import is_real_speech_transcript

    for row in items:
        qid = row.get("q_id")
        res = row.get("result") or {}
        tx_raw = (res.get("transcript") or "")[:1200]
        # Trust gate: even in the PDF export we never persist hallucinated
        # text — readers should see an empty-state marker, not a fabricated
        # transcript.
        no_speech_flag = bool(res.get("no_speech_detected")) or (
            res.get("diagnosis_status") == "no_speech"
        )
        if res.get("diagnosis_status") == "analysis_pending":
            tx = "(AI analysis pending)"
        elif tx_raw and not no_speech_flag and is_real_speech_transcript(tx_raw):
            tx = _pdf_text(tx_raw)
        else:
            tx = "(no speech detected)"
        story.append(
            Paragraph(
                f"<b>Q{qid}</b> · {_pdf_text(row.get('topic', ''))} · <i>{_pdf_text(row.get('type', ''))}</i><br/>"
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
            ParagraphStyle(
                name="Foot",
                parent=styles["Normal"],
                fontName=font_regular,
                fontSize=8,
                textColor=colors.grey,
            ),
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
