"""
Phase 5 — Memo generation.

Assembles the Phase 2 extraction and Phase 3 consistency flags into a
clean, formatted Word document — the actual deliverable, not just
terminal output. Same visual style as the PE screener's memo for a
consistent look across both tools.
"""

import os
from datetime import datetime

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.table import WD_TABLE_ALIGNMENT

ACCENT_COLOR = RGBColor(0x1F, 0x38, 0x64)
LIGHT_GREY = RGBColor(0x66, 0x66, 0x66)
CAUTION_COLOR = RGBColor(0xB0, 0x3A, 0x2E)


def _add_heading(doc: Document, text: str, size: int = 16):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = ACCENT_COLOR


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.style = "Light Grid Accent 1"

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                r.bold = True

    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val) if val is not None else "—"

    return table


def _add_bullet_list(doc: Document, items: list[str]):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def generate_triage_memo(deck_name: str, claims: dict, flags: list[dict], output_dir: str = "output") -> str:
    """
    Builds the pitch deck triage memo .docx and saves it to output_dir.
    Returns the path to the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    company_name = claims.get("company_name") or deck_name

    # --- Title block ---
    title = doc.add_paragraph()
    title_run = title.add_run(f"Pitch Deck Triage Memo — {company_name}")
    title_run.bold = True
    title_run.font.size = Pt(22)
    title_run.font.color.rgb = ACCENT_COLOR

    subtitle = doc.add_paragraph()
    subtitle_run = subtitle.add_run(
        f"{claims.get('one_liner') or 'No one-liner found in deck'} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    subtitle_run.italic = True
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.color.rgb = LIGHT_GREY

    doc.add_paragraph()

    # --- Team ---
    team = claims.get("team") or []
    _add_heading(doc, "Team")
    if team:
        _add_table(
            doc,
            ["Name", "Background Claim", "Slide"],
            [[m.get("name"), m.get("background_claim"), m.get("slide")] for m in team],
        )
    else:
        doc.add_paragraph("No team information found in the deck.")
    doc.add_paragraph()

    # --- Market ---
    market = claims.get("market") or {}
    _add_heading(doc, "Market Sizing")
    if market.get("tam_claim"):
        sourced_label = "sourced" if market.get("tam_sourced") else "NOT sourced to any citation in the deck"
        doc.add_paragraph(f"TAM: {market.get('tam_claim')} ({sourced_label})")
        if market.get("sam_claim"):
            doc.add_paragraph(f"SAM: {market.get('sam_claim')}")
        if market.get("som_claim"):
            doc.add_paragraph(f"SOM: {market.get('som_claim')}")
    else:
        doc.add_paragraph("No market sizing (TAM/SAM/SOM) found in the deck.")
    doc.add_paragraph()

    # --- Traction ---
    traction = claims.get("traction") or []
    _add_heading(doc, "Traction")
    if traction:
        _add_table(
            doc,
            ["Metric", "Value", "Has Growth Rate?", "Slide"],
            [[t.get("metric"), t.get("value"), "Yes" if t.get("has_growth_rate") else "No", t.get("slide")] for t in traction],
        )
    else:
        doc.add_paragraph("No traction metrics found in the deck.")
    doc.add_paragraph()

    # --- Competition ---
    competition = claims.get("competition") or {}
    competitors = competition.get("competitors_mentioned") or []
    _add_heading(doc, "Competitive Landscape")
    if competitors:
        doc.add_paragraph("Competitors mentioned in deck: " + ", ".join(competitors))
    else:
        doc.add_paragraph("No competitors mentioned anywhere in the deck.")
    doc.add_paragraph()

    # --- The Ask ---
    ask = claims.get("ask") or {}
    _add_heading(doc, "The Ask")
    if ask.get("round_size"):
        doc.add_paragraph(f"Round size: {ask.get('round_size')}")
        if ask.get("valuation"):
            doc.add_paragraph(f"Valuation: {ask.get('valuation')}")
        doc.add_paragraph(f"Use of funds: {ask.get('use_of_funds') or 'Not specified in deck'}")
    else:
        doc.add_paragraph("No specific ask (round size) stated in the deck.")
    doc.add_paragraph()

    # --- Flags, split by severity ---
    caution_flags = [f for f in flags if f.get("severity") == "caution"]
    info_flags = [f for f in flags if f.get("severity") == "info"]

    if caution_flags:
        _add_heading(doc, "Risk Flags")
        _add_bullet_list(
            doc,
            [
                f"(Slide {f['slide']}) {f['message']}" if f.get("slide") is not None else f["message"]
                for f in caution_flags
            ],
        )
        doc.add_paragraph()

    if info_flags:
        _add_heading(doc, "Additional Notes")
        _add_bullet_list(
            doc,
            [
                f"(Slide {f['slide']}) {f['message']}" if f.get("slide") is not None else f["message"]
                for f in info_flags
            ],
        )
        doc.add_paragraph()

    if not flags:
        doc.add_paragraph(
            "No flags raised — the deck's claims are well-sourced and complete by these automated checks."
        )
        doc.add_paragraph()

    # --- Disclaimer footer ---
    disclaimer = doc.add_paragraph()
    disclaimer_run = disclaimer.add_run(
        "This memo was generated automatically from the pitch deck's own slides via vision-based LLM "
        "extraction, with rule-based consistency checks applied on top. It is a first-pass triage aid "
        "only, not a substitute for full due diligence. No claim in this memo has been independently "
        "verified against outside sources — every figure above is exactly what the deck itself states, "
        "and should be checked before use in any investment decision."
    )
    disclaimer_run.italic = True
    disclaimer_run.font.size = Pt(8)
    disclaimer_run.font.color.rgb = LIGHT_GREY

    # Timestamped to the second so reruns never collide with a file open elsewhere.
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in deck_name)
    filename = f"{safe_name}_triage_memo_{timestamp}.docx"
    filepath = os.path.join(output_dir, filename)
    doc.save(filepath)
    return filepath
