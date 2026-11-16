"""Generate clearly labeled synthetic policy PDFs and reproducible evaluation truth.
Run: python scripts/generate_samples.py (from repo root)
"""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples"
OUT.mkdir(exist_ok=True)

DOCS = {
    "student_aid": {
        "title": "Student Advancement Support Scheme", "name": "Student Advancement Support Scheme",
        "old": [
            "1. Age eligibility: Applicant age must be between 18 and 25 years (inclusive) as of 2026-07-01.",
            "2. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
            "3. Minimum marks: Applicants must have at least 60% marks in the qualifying degree.",
            "4. Annual family income: Annual family income must not exceed INR 800,000.",
            "5. Category: Only applicants in General, OBC, SC, ST and EWS categories may apply.",
            "6. Application deadline: Applications must be submitted on or before 2026-08-31.",
            "7. Required documents: identity proof, degree certificate and income certificate.",
            "8. Selection note: Merit ranking may be used after initial eligibility screening.",
        ],
        "new": [
            "1. Age eligibility: Applicant age must be between 18 and 27 years (inclusive) as of 2026-07-01.",
            "2. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
            "3. Minimum marks: Applicants must have at least 65% marks in the qualifying degree.",
            "4. Annual family income: Annual family income must not exceed INR 900,000.",
            "5. Category: Only applicants in General, OBC, SC, ST and EWS categories may apply.",
            "6. Application deadline: Applications must be submitted on or before 2026-09-15.",
            "7. Required documents: identity proof, degree certificate, income certificate and residence proof.",
            "8. Help desk: For application queries, consult the designated help desk.",
        ],
    },
    "fellowship": {
        "title": "Regional Skills Fellowship", "name": "Regional Skills Fellowship",
        "old": [
            "1. Age eligibility: Applicant age must be between 21 and 30 years as of 2026-07-01.",
            "2. Academic qualification: Applicants must hold a Master's degree in any discipline.",
            "3. Minimum marks: Applicants must have at least 70% marks in the qualifying degree.",
            "4. Annual income: Annual family income must not exceed INR 1,200,000.",
            "5. Application deadline: Applications must be submitted on or before 2026-05-01.",
            "6. Required documents: identity proof and degree certificate.",
        ],
        "new": [
            "1. Age eligibility: Applicant age must be between 21 and 32 years as of 2026-07-01.",
            "2. Academic qualification: Applicants must hold a Master's degree in any discipline.",
            "3. Minimum marks: Applicants must have at least 70% marks in the qualifying degree.",
            "4. Annual income: Annual family income must not exceed INR 1,200,000.",
            "5. Application deadline: Applications must be submitted on or before 2026-06-01.",
            "6. Required documents: identity proof and degree certificate.",
        ],
    },
    "research_grant": {
        "title": "Community Research Grant", "name": "Community Research Grant",
        "old": [
            "1. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
            "2. Minimum marks: Applicants must have at least 55% marks in the qualifying degree.",
            "3. Annual family income: Annual family income must not exceed INR 1,000,000.",
            "4. Application deadline: Applications must be submitted on or before 2026-10-15.",
            "5. Required documents: identity proof and degree certificate.",
            "6. Contact: Questions may be sent to the district office.",
        ],
        "new": [
            "1. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
            "2. Minimum marks: Applicants must have at least 55% marks in the qualifying degree.",
            "3. Annual family income: Annual family income must not exceed INR 1,200,000.",
            "4. Application deadline: Applications must be submitted on or before 2026-10-15.",
            "5. Required documents: identity proof and degree certificate.",
            "6. Contact: For questions, reach out to the district office.",
        ],
    },
    "contradictory": {
        "title": "Experimental Merit Award", "name": "Experimental Merit Award",
        "old": [
            "1. Minimum marks: Applicants must have at least 60% marks in the qualifying degree.",
            "2. Maximum marks: Applicants must have at most 90% marks in the qualifying degree.",
            "3. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
        ],
        "new": [
            "1. Minimum marks: Applicants must have at least 80% marks in the qualifying degree.",
            "2. Maximum marks: Applicants must have at most 70% marks in the qualifying degree.",
            "3. Academic qualification: Applicants must hold a Bachelor's degree in any discipline.",
        ],
    },
}


def make_pdf(destination: Path, title: str, subtitle: str, clauses: list[str]):
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("main", parent=styles["Title"], fontSize=19, leading=25, textColor=colors.HexColor("#143349"), spaceAfter=15)
    subtitle_style = ParagraphStyle("sub", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, textColor=colors.HexColor("#607184"), spaceAfter=18)
    clause_style = ParagraphStyle("clause", parent=styles["BodyText"], fontSize=10.5, leading=16, spaceAfter=19)
    doc = SimpleDocTemplate(str(destination), pagesize=(612, 792), leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = [Paragraph(escape(title), heading), Paragraph(escape(subtitle), subtitle_style),
             Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT ISSUED BY ANY GOVERNMENT OR INSTITUTION", subtitle_style),
             HRFlowable(width="100%", color=colors.HexColor("#d5e1e8")), Spacer(1, 10),
             Paragraph("All names, dates and criteria below are fictional and used only for software evaluation.", subtitle_style), Spacer(1, 12)]
    story.extend(Paragraph(escape(line), clause_style) for line in clauses)
    doc.build(story)


def profile(name, dob=None, level=None, marks=None, income=None, category=None, submitted=None, documents=None):
    return {"name": name, "details": {"date_of_birth": dob, "education_level": level, "marks": marks,
                                       "annual_income": income, "category": category, "application_date": submitted, "documents": documents}}


STUDENT_DOCS = ["identity proof", "degree certificate", "income certificate"]
STUDENT_NEW_DOCS = STUDENT_DOCS + ["residence proof"]
FELLOW_DOCS = ["identity proof", "degree certificate"]
CASES = [
    {"policy": "student_aid", "applicant": profile("Asha – marks tightened", "2003-01-01", "bachelor", 62, 700000, "EWS", "2026-08-15", STUDENT_DOCS), "before": "eligible", "after": "ineligible"},
    {"policy": "student_aid", "applicant": profile("Rohan – newly eligible", "2000-03-01", "bachelor", 80, 820000, "General", "2026-09-05", STUDENT_NEW_DOCS), "before": "ineligible", "after": "eligible"},
    {"policy": "student_aid", "applicant": profile("Meera – no impact", "2002-02-01", "bachelor", 74, 730000, "OBC", "2026-08-01", STUDENT_NEW_DOCS), "before": "eligible", "after": "eligible"},
    {"policy": "student_aid", "applicant": profile("Nikhil – still ineligible", "2006-05-15", "bachelor", 55, 500000, "SC", "2026-07-01", STUDENT_NEW_DOCS), "before": "ineligible", "after": "ineligible"},
    {"policy": "student_aid", "applicant": profile("Unknown marks", "2001-03-01", "bachelor", None, 500000, "General", "2026-08-10", STUDENT_NEW_DOCS), "before": "undetermined", "after": "undetermined"},
    {"policy": "student_aid", "applicant": profile("Unknown documents", "2002-03-01", "bachelor", 80, 500000, "General", "2026-08-10", None), "before": "undetermined", "after": "undetermined"},
    {"policy": "fellowship", "applicant": profile("Rita – age and deadline eased", "1995-05-01", "master", 76, 600000, "General", "2026-05-15", FELLOW_DOCS), "before": "ineligible", "after": "eligible"},
    {"policy": "fellowship", "applicant": profile("Vivek – unchanged eligible", "1998-04-01", "master", 80, 700000, "OBC", "2026-04-15", FELLOW_DOCS), "before": "eligible", "after": "eligible"},
    {"policy": "fellowship", "applicant": profile("Farah – too old for both", "1991-01-01", "master", 82, 600000, "SC", "2026-04-15", FELLOW_DOCS), "before": "ineligible", "after": "ineligible"},
    {"policy": "fellowship", "applicant": profile("Application date unknown", "1998-04-01", "master", 78, 650000, "General", None, FELLOW_DOCS), "before": "undetermined", "after": "undetermined"},
    {"policy": "research_grant", "applicant": profile("Anu – income relaxed", "2001-03-01", "bachelor", 72, 1100000, "General", "2026-09-01", FELLOW_DOCS), "before": "ineligible", "after": "eligible"},
    {"policy": "research_grant", "applicant": profile("Dev – unchanged eligible", "2001-01-01", "master", 65, 600000, "OBC", "2026-09-01", FELLOW_DOCS), "before": "eligible", "after": "eligible"},
    {"policy": "research_grant", "applicant": profile("Sara – over both incomes", "2001-01-01", "bachelor", 65, 1400000, "General", "2026-09-01", FELLOW_DOCS), "before": "ineligible", "after": "ineligible"},
    {"policy": "contradictory", "applicant": profile("Isha – conflicting rules", "2000-01-01", "bachelor", 75, 600000, "General", "2026-04-01", FELLOW_DOCS), "before": "eligible", "after": "undetermined"},
    {"policy": "contradictory", "applicant": profile("Akash – conflict overrides outcome", "2000-01-01", "bachelor", 95, 600000, "General", "2026-04-01", FELLOW_DOCS), "before": "ineligible", "after": "undetermined"},
]


def main():
    for slug, entry in DOCS.items():
        for version in ("old", "new"):
            make_pdf(OUT / f"{slug}_{version}.pdf", entry["title"], f"{version.capitalize()} version • policy year 2026", entry[version])
    profiles = [item["applicant"] for item in CASES[:7]]
    (OUT / "demo_applicants.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    (OUT / "evaluation_cases.json").write_text(json.dumps({"version": 1, "synthetic": True, "cases": CASES}, indent=2), encoding="utf-8")
    print(f"Generated {len(DOCS) * 2} synthetic PDFs and {len(CASES)} labeled evaluation cases in {OUT}")


if __name__ == "__main__":
    main()
