"""Locally generated evidence-backed PDF comparison reports."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def make_report(policy_name: str, old_label: str, new_label: str, applicant_name: str, result: dict) -> bytes:
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=(612, 792), leftMargin=46, rightMargin=46, topMargin=45, bottomMargin=43,
                            title="RuleShift Evidence-Grounded Comparison", author="RuleShift local application")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="LeadCustom", parent=styles["Normal"], fontSize=10.5, leading=16, textColor=colors.HexColor("#3f536a"), spaceAfter=13))
    styles.add(ParagraphStyle(name="EvidenceCustom", parent=styles["Normal"], fontSize=8.3, leading=12, textColor=colors.HexColor("#34465e"), spaceAfter=8))
    styles.add(ParagraphStyle(name="HeadingCustom", parent=styles["Heading2"], textColor=colors.HexColor("#14283f"), spaceBefore=13, spaceAfter=7))
    styles.add(ParagraphStyle(name="TinyCustom", parent=styles["Normal"], fontSize=8, leading=11))
    flow = [Paragraph("RuleShift / Policy change report", styles["Title"]), Spacer(1, 8),
            Paragraph(escape(policy_name), styles["HeadingCustom"]),
            Paragraph(f"Applicant: {escape(applicant_name)}<br/>{escape(old_label)}  →  {escape(new_label)}", styles["LeadCustom"])]
    row_data = [["BEFORE", "AFTER"], [result["before"]["status"].upper(), result["after"]["status"].upper()]]
    table = Table(row_data, colWidths=[258, 258], rowHeights=[23, 38])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf1f5")),
                               ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f7fafc")),
                               ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#163a50")),
                               ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                               ("PADDING", (0, 0), (-1, -1), 9)]))
    flow += [table, Spacer(1, 12), Paragraph(escape(result["disclaimer"]), styles["EvidenceCustom"])]
    counts = result["comparison"]["counts"]
    flow += [Paragraph("Clause changes", styles["HeadingCustom"]),
             Paragraph("  •  ".join(f"{key.capitalize()}: {value}" for key, value in counts.items()), styles["Normal"])]
    flow.append(Paragraph("Applicant-specific rule impacts", styles["HeadingCustom"]))
    if not result["applicant_impacts"]:
        flow.append(Paragraph("No changed clauses altered a checked field outcome for this applicant.", styles["Normal"]))
    for item in result["applicant_impacts"]:
        bits = [Paragraph(f"<b>{escape(item['field'])}</b> — {escape(item['before'])} → {escape(item['after'])}", styles["Normal"])]
        for label, clause in (("Previous", item["old_clause"]), ("Updated", item["new_clause"])):
            if clause:
                bits.append(Paragraph(f"{label} [p. {clause['page']}]: {escape(clause['text'][:600])}", styles["EvidenceCustom"]))
        flow.append(KeepTogether(bits))
    for side in ("before", "after"):
        flow.append(Paragraph(f"Rule-level checks: {side.capitalize()}", styles["HeadingCustom"]))
        info = result[side]
        for check in info["rule_checks"]:
            flow.append(Paragraph(f"<b>{escape(check['field'])}</b> [{escape(check['status'])}] — {escape(check['detail'])}", styles["TinyCustom"]))
            flow.append(Paragraph(f"Source p. {check['page']}: {escape(check['evidence_text'][:400])}", styles["EvidenceCustom"]))
        for warning in info["warnings"]:
            flow.append(Paragraph(f"Review warning p. {warning.get('page', '?')}: {escape(warning['message'])}", styles["EvidenceCustom"]))
        for conflict in info["conflicts"]:
            flow.append(Paragraph(f"Conflict: {escape(conflict['message'])}", styles["EvidenceCustom"]))
        if info["missing_fields"]:
            flow.append(Paragraph("Missing profile fields: " + escape(", ".join(info["missing_fields"])), styles["EvidenceCustom"]))
    doc.build(flow)
    return out.getvalue()
