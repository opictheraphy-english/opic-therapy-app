"""Mock V2 final report PDF — premium layout aligned with on-screen report."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from services.mock_v2_report_display import (
    answered_summary_label,
    diagnosis_tip_text,
    hero_note,
    level_gap_chip_text,
    list_strengths_weaknesses,
    metric_chip_labels,
    overall_raw_from_agg,
    row_better_direction,
    row_feedback_text,
    row_is_no_response,
    row_level_display,
    sorted_rubric_bars,
    today_kst_label,
    transcript_for_export,
)
from services.pdf_report import _pdf_text, pdf_export_available, _register_pdf_fonts
from ui.design_tokens import (
    BRAND_300,
    BRAND_500,
    BRAND_700,
    BRAND_900,
    ON_GREEN_SUB,
    TEXT_400,
    TEXT_600,
    TEXT_900,
)

logger = logging.getLogger(__name__)

_PDF_AMBER_BG = "#fffaf0"
_PDF_AMBER_BORDER = "#f3e3c3"
_PDF_AMBER_TEXT = "#6b5330"
_PDF_AMBER_WARN = "#b06428"
_PDF_AMBER_BAR = "#e0a35c"
_PDF_FEEDBACK_BG = "#eefaf5"
_PDF_ANSWER_BG = "#f8faf8"
_PDF_BAR_TRACK = "#eef1ee"
_PDF_CHIP_BG = "#0f5443"
_PDF_BORDER_SOFT = "#eceee9"


def _hex_color(hex_code: str) -> Any:
    from reportlab.lib import colors

    return colors.HexColor(hex_code)


class _HBar:
    """Horizontal score bar (track + fill)."""

    def __init__(
        self,
        pct: float,
        *,
        fill: str = BRAND_500,
        width: float = 16.0,
        height: float = 0.18,
    ) -> None:
        from reportlab.platypus import Flowable

        class Bar(Flowable):
            def __init__(self_inner) -> None:
                Flowable.__init__(self_inner)
                self_inner.pct = max(4.0, min(100.0, float(pct)))
                self_inner.fill = fill
                self_inner.bar_width = width * 28.35  # cm-ish via caller
                self_inner.bar_height = height * 28.35

            def wrap(self_inner, availWidth: float, availHeight: float) -> Tuple[float, float]:
                self_inner._w = min(self_inner.bar_width, availWidth)
                return self_inner._w, self_inner.bar_height + 2

            def draw(self_inner) -> None:
                c = self_inner.canv
                y = 1
                c.setFillColor(_hex_color(_PDF_BAR_TRACK))
                c.roundRect(0, y, self_inner._w, self_inner.bar_height, 1.5, fill=1, stroke=0)
                c.setFillColor(_hex_color(self_inner.fill))
                fill_w = self_inner._w * self_inner.pct / 100.0
                c.roundRect(0, y, fill_w, self_inner.bar_height, 1.5, fill=1, stroke=0)

        self._flowable = Bar()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._flowable, name)


def _make_hbar(pct: float, *, fill: str, width_cm: float) -> Any:
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import Flowable

    class Bar(Flowable):
        def __init__(self) -> None:
            super().__init__()
            self.pct = max(4.0, min(100.0, float(pct)))
            self.fill = fill
            self.bar_width = width_cm * cm
            self.bar_height = 5 * mm

        def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
            self._w = min(self.bar_width, availWidth)
            return self._w, self.bar_height + 2 * mm

        def draw(self) -> None:
            c = self.canv
            y = 1 * mm
            c.setFillColor(_hex_color(_PDF_BAR_TRACK))
            c.roundRect(0, y, self._w, self.bar_height, 1.5, fill=1, stroke=0)
            c.setFillColor(_hex_color(self.fill))
            fill_w = self._w * self.pct / 100.0
            c.roundRect(0, y, fill_w, self.bar_height, 1.5, fill=1, stroke=0)

    return Bar()


def _styles(font_regular: str, font_bold: str) -> Dict[str, Any]:
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    return {
        "brand": ParagraphStyle(
            "m2Brand",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=colors.white,
        ),
        "brand_sub": ParagraphStyle(
            "m2BrandSub",
            fontName=font_regular,
            fontSize=9,
            leading=12,
            textColor=_hex_color(BRAND_300),
        ),
        "hero_label": ParagraphStyle(
            "m2HeroLabel",
            fontName=font_regular,
            fontSize=9,
            leading=12,
            textColor=_hex_color(BRAND_300),
        ),
        "hero_grade": ParagraphStyle(
            "m2HeroGrade",
            fontName=font_bold,
            fontSize=42,
            leading=46,
            textColor=colors.white,
        ),
        "hero_conf": ParagraphStyle(
            "m2HeroConf",
            fontName=font_regular,
            fontSize=10,
            leading=13,
            textColor=_hex_color(BRAND_300),
        ),
        "hero_note": ParagraphStyle(
            "m2HeroNote",
            fontName=font_regular,
            fontSize=10.5,
            leading=16,
            textColor=_hex_color(ON_GREEN_SUB),
        ),
        "chip": ParagraphStyle(
            "m2Chip",
            fontName=font_regular,
            fontSize=9,
            leading=11,
            textColor=_hex_color(BRAND_300),
        ),
        "h2": ParagraphStyle(
            "m2H2",
            fontName=font_bold,
            fontSize=12.5,
            leading=16,
            textColor=_hex_color(TEXT_900),
            spaceBefore=6,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "m2Body",
            fontName=font_regular,
            fontSize=10.5,
            leading=15,
            textColor=_hex_color(TEXT_600),
        ),
        "body_dark": ParagraphStyle(
            "m2BodyDark",
            fontName=font_regular,
            fontSize=10.5,
            leading=15,
            textColor=_hex_color(TEXT_900),
        ),
        "tip": ParagraphStyle(
            "m2Tip",
            fontName=font_regular,
            fontSize=9.5,
            leading=13,
            textColor=_hex_color(TEXT_400),
        ),
        "q_title": ParagraphStyle(
            "m2QTitle",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=_hex_color(TEXT_900),
        ),
        "q_meta": ParagraphStyle(
            "m2QMeta",
            fontName=font_regular,
            fontSize=9,
            leading=12,
            textColor=_hex_color(TEXT_400),
        ),
        "q_question": ParagraphStyle(
            "m2QQ",
            fontName=font_bold,
            fontSize=10.5,
            leading=14,
            textColor=_hex_color(TEXT_900),
        ),
        "transcript": ParagraphStyle(
            "m2Tx",
            fontName=font_regular,
            fontSize=9.5,
            leading=14,
            textColor=_hex_color(TEXT_600),
        ),
        "feedback": ParagraphStyle(
            "m2Fb",
            fontName=font_regular,
            fontSize=10,
            leading=16,
            textColor=_hex_color("#3d5147"),
        ),
        "better": ParagraphStyle(
            "m2Better",
            fontName=font_regular,
            fontSize=10,
            leading=16,
            textColor=_hex_color(_PDF_AMBER_TEXT),
        ),
        "mission_title": ParagraphStyle(
            "m2MissionT",
            fontName=font_bold,
            fontSize=12,
            leading=15,
            textColor=_hex_color("#7a4a0c"),
        ),
        "mission_body": ParagraphStyle(
            "m2MissionB",
            fontName=font_regular,
            fontSize=10.5,
            leading=17,
            textColor=_hex_color(_PDF_AMBER_TEXT),
        ),
        "footer": ParagraphStyle(
            "m2Footer",
            fontName=font_regular,
            fontSize=8.5,
            leading=12,
            textColor=_hex_color(TEXT_400),
            alignment=TA_LEFT,
        ),
        "sw_title_good": ParagraphStyle(
            "m2SwGood",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=_hex_color(BRAND_700),
        ),
        "sw_title_warn": ParagraphStyle(
            "m2SwWarn",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=_hex_color(_PDF_AMBER_WARN),
        ),
        "sw_item": ParagraphStyle(
            "m2SwItem",
            fontName=font_regular,
            fontSize=10,
            leading=14,
            textColor=_hex_color(TEXT_600),
        ),
    }


def _header_footer(canvas: Any, doc: Any, *, font_regular: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm

    canvas.saveState()
    canvas.setFont(font_regular, 7.5)
    canvas.setFillColor(_hex_color(TEXT_400))
    canvas.drawString(doc.leftMargin, A4[1] - 1.0 * cm, "오픽치료사 OPIc Report")
    canvas.drawRightString(
        A4[0] - doc.rightMargin,
        0.85 * cm,
        f"{canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _card_table(
    flowables: List[Any],
    *,
    bg: str = "#ffffff",
    padding: int = 12,
) -> Any:
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle

    inner = [[f] for f in flowables]
    t = Table(inner, colWidths=[16.8 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex_color(bg)),
                ("BOX", (0, 0), (-1, -1), 0.5, _hex_color(_PDF_BORDER_SOFT)),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def _brand_cover_band(date_label: str, patient_label: str, st: Dict[str, Any]) -> Any:
    from reportlab.platypus import Paragraph, Table, TableStyle

    title = Paragraph("오픽치료사 · OPIc 실전 모의고사 리포트", st["brand"])
    meta_parts = [date_label]
    if patient_label and patient_label not in (
        "OPIc Mock V2 Report",
        "OPIc Sample Report",
    ):
        meta_parts.append(patient_label)
    meta = Paragraph(" · ".join(meta_parts), st["brand_sub"])
    inner = Table([[title], [meta]], colWidths=[16.8 * cm])
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex_color(BRAND_900)),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
            ]
        )
    )
    return inner


def _hero_block(
    overall_raw: str,
    confidence: Any,
    note: str,
    st: Dict[str, Any],
) -> Any:
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    conf_txt = ""
    try:
        if confidence is not None and str(confidence).strip() != "":
            conf_txt = f"신뢰도 {int(float(confidence))}%"
    except (TypeError, ValueError):
        conf_txt = ""

    grade_cells: List[Any] = [Paragraph(_pdf_text(overall_raw or "—"), st["hero_grade"])]
    if conf_txt:
        grade_cells.extend(
            [Spacer(1, 4), Paragraph(_pdf_text(conf_txt), st["hero_conf"])]
        )
    inner_rows: List[List[Any]] = [
        [Paragraph("종합 예측 등급", st["hero_label"])],
        [Table([grade_cells])],
    ]
    if note.strip():
        inner_rows.append([Paragraph(_pdf_text(note), st["hero_note"])])
    inner = Table(inner_rows, colWidths=[16.4 * cm])
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex_color(BRAND_900)),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
            ]
        )
    )
    return inner


def _chips_row(chips: List[str], st: Dict[str, Any]) -> Any:
    from reportlab.platypus import Paragraph, Table, TableStyle

    cells = []
    for chip in chips:
        p = Paragraph(_pdf_text(chip), st["chip"])
        cells.append(
            Table(
                [[p]],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), _hex_color(_PDF_CHIP_BG)),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                ),
            )
        )
    row = Table([cells])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return row


def _diagnosis_section(
    rubric: Dict[str, Any],
    overall_raw: str,
    st: Dict[str, Any],
) -> List[Any]:
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    bars = sorted_rubric_bars(rubric)
    if not bars:
        return [
            Paragraph("영역별 진단", st["h2"]),
            Paragraph("세션 점수 데이터가 없습니다.", st["body"]),
        ]
    lowest_score = min(v for _, v in bars)
    lowest_labels = {lbl for lbl, v in bars if v == lowest_score}
    out: List[Any] = [Paragraph("영역별 진단", st["h2"])]
    for label, score in bars:
        is_low = label in lowest_labels and len(bars) > 1
        val_color = _PDF_AMBER_WARN if is_low else BRAND_700
        head = Table(
            [
                [
                    Paragraph(_pdf_text(label), st["body_dark"]),
                    Paragraph(
                        f'<font color="{val_color}">{score:.0f}</font>',
                        st["body_dark"],
                    ),
                ]
            ],
            colWidths=[12 * cm, 4 * cm],
        )
        head.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        out.append(head)
        out.append(_make_hbar(score, fill=_PDF_AMBER_BAR if is_low else BRAND_500, width_cm=16.0))
        out.append(Spacer(1, 2 * mm))
    tip = diagnosis_tip_text(bars, overall_raw)
    if tip:
        out.append(Paragraph(_pdf_text(tip), st["tip"]))
    return out


def _sw_section(
    strengths: List[str],
    weaknesses: List[str],
    st: Dict[str, Any],
) -> Optional[Any]:
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    if not strengths and not weaknesses:
        return None
    s_body = [Paragraph(f"• {_pdf_text(t)}", st["sw_item"]) for t in strengths] or [
        Paragraph("—", st["sw_item"])
    ]
    w_body = [Paragraph(f"• {_pdf_text(t)}", st["sw_item"]) for t in weaknesses] or [
        Paragraph("—", st["sw_item"])
    ]
    left = [[Paragraph("잘한 점", st["sw_title_good"])]] + [[p] for p in s_body]
    right = [[Paragraph("보완할 점", st["sw_title_warn"])]] + [[p] for p in w_body]
    grid = Table(
        [[Table(left, colWidths=[7.8 * cm]), Table(right, colWidths=[7.8 * cm])]],
        colWidths=[8.2 * cm, 8.2 * cm],
    )
    grid.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, _hex_color(_PDF_BORDER_SOFT)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return grid


def _question_card(row: Dict[str, Any], st: Dict[str, Any]) -> List[Any]:
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer

    qid = int(row.get("q_id") or 0)
    res = row.get("result") or {}
    topic = str(row.get("topic") or "—")
    typ = str(row.get("type") or "—")
    no_resp = row_is_no_response(res)
    lvl = row_level_display(res)

    meta_parts = [f"Q{qid}", topic, typ]
    if no_resp:
        meta_parts.insert(2, "미응답")
    elif lvl and lvl not in ("—", "분석 대기"):
        meta_parts.insert(2, lvl)

    parts: List[Any] = [
        Paragraph(" · ".join(_pdf_text(p) for p in meta_parts), st["q_title"]),
    ]
    question = str(row.get("question") or "").strip()
    if question:
        parts.append(Paragraph(_pdf_text(question), st["q_question"]))
    chips = metric_chip_labels(res)
    if chips:
        parts.append(Paragraph(_pdf_text(" · ".join(chips)), st["q_meta"]))

    if no_resp:
        parts.append(Spacer(1, 2 * mm))
        parts.append(
            _card_table(
                [Paragraph("응답이 기록되지 않았어요.", st["body"])],
                bg=_PDF_ANSWER_BG,
            )
        )
        fb = row_feedback_text(res) or "응답이 충분하지 않았어요."
        parts.append(Spacer(1, 2 * mm))
        parts.append(
            _card_table(
                [
                    Paragraph("<b>피드백</b>", st["body_dark"]),
                    Paragraph(_pdf_text(fb), st["feedback"]),
                ],
                bg=_PDF_FEEDBACK_BG,
            )
        )
    else:
        tx, has_tx = transcript_for_export(res)
        parts.append(Spacer(1, 2 * mm))
        tx_flow: List[Any] = [Paragraph("<b>내 답변</b>", st["body_dark"])]
        if has_tx and tx:
            tx_flow.append(Paragraph(_pdf_text(tx), st["transcript"]))
        else:
            tx_flow.append(Paragraph("응답이 기록되지 않았어요.", st["transcript"]))
        parts.append(_card_table(tx_flow, bg=_PDF_ANSWER_BG))

        fb = row_feedback_text(res)
        if fb:
            parts.append(Spacer(1, 2 * mm))
            parts.append(
                _card_table(
                    [
                        Paragraph("<b>피드백</b>", st["body_dark"]),
                        Paragraph(_pdf_text(fb), st["feedback"]),
                    ],
                    bg=_PDF_FEEDBACK_BG,
                )
            )
        better = row_better_direction(res)
        if better and better != "—":
            parts.append(Spacer(1, 2 * mm))
            parts.append(
                _card_table(
                    [
                        Paragraph("<b>이렇게 올려보세요</b>", st["body_dark"]),
                        Paragraph(_pdf_text(better), st["better"]),
                    ],
                    bg=_PDF_AMBER_BG,
                )
            )

    parts.insert(0, Spacer(1, 3 * mm))
    return parts


def build_mock_v2_exam_pdf(
    aggregates: Dict[str, Any],
    items: List[Dict[str, Any]],
    report: Dict[str, Any],
    *,
    patient_label: str = "",
    target_level: str = "IH",
    stats: Optional[Dict[str, int]] = None,
) -> Optional[bytes]:
    """Build premium Mock V2 PDF aligned with on-screen final report."""
    if not pdf_export_available():
        logger.info("Mock V2 PDF skipped: reportlab not installed")
        return None

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        font_regular, font_bold = _register_pdf_fonts()
        st = _styles(font_regular, font_bold)
        buf = BytesIO()

        def on_page(canvas: Any, doc: Any) -> None:
            _header_footer(canvas, doc, font_regular=font_regular)

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=1.8 * cm,
            leftMargin=1.8 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.4 * cm,
            title="OPIc Mock V2 Report",
        )

        story: List[Any] = []
        date_label = today_kst_label()
        overall_raw = overall_raw_from_agg(aggregates)
        note = hero_note(report if isinstance(report, dict) else {}, aggregates)
        conf = aggregates.get("confidence", 0)

        if stats is None:
            from services.exam_analytics import exam_results_summary_stats

            stats = exam_results_summary_stats(items)

        answered_label = answered_summary_label(stats)
        gap_chip = level_gap_chip_text(overall_raw, target_level)

        wpm_txt = aggregates.get("avg_wpm", "—")
        try:
            wpm_chip = (
                f"평균 {float(wpm_txt):.0f} WPM"
                if wpm_txt not in (None, "", "—")
                else "평균 — WPM"
            )
        except (TypeError, ValueError):
            wpm_chip = f"평균 {wpm_txt} WPM"

        story.append(_brand_cover_band(date_label, patient_label, st))
        story.append(Spacer(1, 4 * mm))
        story.append(_hero_block(overall_raw, conf, note, st))
        story.append(Spacer(1, 4 * mm))
        story.append(_chips_row([wpm_chip, f"답변 {answered_label}", gap_chip], st))
        story.append(Spacer(1, 5 * mm))

        rubric = aggregates.get("rubric_averages") or {}
        story.append(_card_table(_diagnosis_section(rubric, overall_raw, st), padding=12))
        story.append(Spacer(1, 4 * mm))

        strengths, weaknesses = list_strengths_weaknesses(
            report if isinstance(report, dict) else {}
        )
        sw = _sw_section(strengths, weaknesses, st)
        if sw is not None:
            story.append(sw)
            story.append(Spacer(1, 4 * mm))

        story.append(PageBreak())
        story.append(Paragraph("문항별 상세", st["h2"]))
        story.append(Spacer(1, 2 * mm))

        for row in sorted(items, key=lambda x: int(x.get("q_id") or 0)):
            if isinstance(row, dict):
                story.append(KeepTogether(_question_card(row, st)))

        mission = str((report or {}).get("practice_mission") or "").strip()
        story.append(PageBreak())
        if mission:
            mission_inner = _card_table(
                [
                    Paragraph("이번 주 처방", st["mission_title"]),
                    Spacer(1, 2 * mm),
                    Paragraph(_pdf_text(mission), st["mission_body"]),
                ],
                bg=_PDF_AMBER_BG,
                padding=14,
            )
            mission_wrap = Table([[mission_inner]], colWidths=[16.8 * cm])
            mission_wrap.setStyle(
                TableStyle([("BOX", (0, 0), (-1, -1), 0.5, _hex_color(_PDF_AMBER_BORDER))])
            )
            story.append(mission_wrap)
            story.append(Spacer(1, 6 * mm))

        story.append(
            Paragraph(
                _pdf_text(
                    "이 리포트는 자기학습용이며 공식 OPIc 성적을 대체하지 않습니다."
                ),
                st["footer"],
            )
        )
        story.append(Paragraph(_pdf_text("© opictherapist"), st["footer"]))

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        data = buf.getvalue()
        buf.close()
        return data
    except Exception as exc:
        logger.exception("Mock V2 PDF build failed: %s", exc)
        return None
