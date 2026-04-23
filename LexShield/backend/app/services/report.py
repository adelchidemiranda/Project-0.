"""
PDF Report Generator using ReportLab
Extended with enriched finding fields and cross-document analysis support.
"""
from __future__ import annotations
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

DARK_NAVY = colors.HexColor("#1a1f36")
GOLD = colors.HexColor("#C9A84C")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
MED_GRAY = colors.HexColor("#888888")

SEVERITY_COLORS = {
    "Critical": colors.HexColor("#dc2626"),
    "High": colors.HexColor("#ea580c"),
    "Medium": colors.HexColor("#d97706"),
    "Low": colors.HexColor("#2563eb"),
}

FINDING_TYPE_LABELS = {
    "internal": "Criticità Interna",
    "cross_document": "Confronto Documentale",
    "strengthening": "Da Rafforzare",
    "attack": "Punto di Attacco",
    "normative_gap": "Lacuna Normativa",
}


def generate_pdf_report(doc, analysis, findings) -> bytes:
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Cover ──────────────────────────────────────────────────────
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=28, textColor=DARK_NAVY, spaceAfter=6)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=13, textColor=GOLD, spaceAfter=4)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=MED_GRAY, spaceAfter=3)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading1"], fontSize=16, textColor=DARK_NAVY, spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, spaceAfter=4, leading=14)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, spaceAfter=3, leading=12, textColor=MED_GRAY)

    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("⚖ LexShield", sub_style))
    story.append(Paragraph("Report Analisi Documentale", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=12))
    story.append(Paragraph(f"<b>Documento:</b> {doc.filename}", meta_style))
    story.append(Paragraph(f"<b>Tipo:</b> {doc.doc_type.upper()}  |  <b>Ruolo:</b> {'Mio Documento' if doc.doc_role == 'mine' else 'Documento Controparte'}  |  <b>Lingua:</b> {doc.language.upper()}", meta_style))
    story.append(Paragraph(f"<b>Generato:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", meta_style))

    # Show documents considered if available
    if analysis.documents_considered:
        docs_list = analysis.documents_considered
        if isinstance(docs_list, list) and len(docs_list) > 1:
            doc_names = ", ".join(d.get("filename", "?") for d in docs_list if d.get("role") != "documento_principale")
            story.append(Paragraph(f"<b>Documenti di supporto considerati:</b> {doc_names}", meta_style))

    story.append(Spacer(1, 0.8*cm))

    # ── Score Summary ───────────────────────────────────────────────
    score = round(analysis.total_score or 0)
    story.append(Paragraph("Riepilogo Punteggio", heading_style))

    score_data = [["Punteggio Totale", f"{score}/100", _score_label(score)]]
    score_table = Table(score_data, colWidths=[6*cm, 4*cm, 5*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 14),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_NAVY]),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 1, GOLD),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5*cm))

    # Sub-scores
    subscores = analysis.subscores or {}
    if subscores:
        story.append(Paragraph("Dettaglio Sub-Punteggi", heading_style))
        subdata = [["Dimensione", "Punteggio"]] + [
            [dim.replace("_", " ").title(), f"{round(val)}/100"]
            for dim, val in subscores.items()
        ]
        sub_table = Table(subdata, colWidths=[10*cm, 4*cm])
        sub_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sub_table)
        story.append(Spacer(1, 0.5*cm))

    # ── Findings ────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph(f"Rilievi ({len(findings)} totali)", heading_style))

    for i, f in enumerate(sorted(findings, key=lambda x: list(SEVERITY_COLORS.keys()).index(x.severity) if x.severity in SEVERITY_COLORS else 4), 1):
        sev_color = SEVERITY_COLORS.get(f.severity, MED_GRAY)
        finding_type_label = FINDING_TYPE_LABELS.get(getattr(f, 'finding_type', 'internal'), 'Criticità Interna')

        # Build finding data rows
        finding_data = [
            [f"#{i} — {f.severity.upper()}", f"{f.category} | {finding_type_label}"],
            ["Estratto:", Paragraph(f.claim[:300], body_style)],
            ["Problema:", Paragraph(f.why_weak, body_style)],
        ]

        # Add enriched fields if present
        cosa_manca = getattr(f, 'cosa_manca', None)
        if cosa_manca:
            finding_data.append(["Cosa manca:", Paragraph(cosa_manca, body_style)])

        base_normativa = getattr(f, 'base_normativa', None)
        if base_normativa:
            finding_data.append(["Base normativa:", Paragraph(base_normativa, body_style)])

        come_attacca = getattr(f, 'come_attacca_controparte', None) or f.opponent_angle
        if come_attacca:
            finding_data.append(["Controparte:", Paragraph(come_attacca or "—", body_style)])

        come_rafforzare = getattr(f, 'come_rafforzare', None) or f.strengthen_suggestion
        if come_rafforzare:
            finding_data.append(["Rafforzamento:", Paragraph(come_rafforzare or "—", body_style)])

        if f.attack_suggestion:
            finding_data.append(["Attacco:", Paragraph(f.attack_suggestion, body_style)])

        impatto = getattr(f, 'impatto_potenziale', None)
        if impatto:
            finding_data.append(["Impatto:", Paragraph(impatto, body_style)])

        verificare = getattr(f, 'elementi_da_verificare', None)
        if verificare:
            finding_data.append(["Da verificare:", Paragraph(verificare, small_style)])

        t = Table(finding_data, colWidths=[4*cm, 11*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), sev_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("SPAN", (0, 0), (0, 0)),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())
    story.append(Paragraph("Disclaimer", heading_style))
    story.append(Paragraph(
        "Questo report è stato generato da LexShield come strumento di supporto redazionale. "
        "NON costituisce parere legale e non sostituisce il giudizio del professionista qualificato. "
        "I riferimenti normativi contrassegnati con [DA VERIFICARE] richiedono conferma da parte del legale. "
        "Tutti i suggerimenti indicano tipologie di fonti da consultare, non citazioni specifiche verificate.",
        body_style
    ))

    pdf.build(story)
    return buffer.getvalue()


def _score_label(score: int) -> str:
    if score >= 85: return "FORTE"
    elif score >= 70: return "ACCETTABILE"
    elif score >= 50: return "VULNERABILE"
    elif score >= 30: return "DEBOLE"
    else: return "CRITICO"
