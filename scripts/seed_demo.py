"""Idempotently load all included synthetic PDFs and applicant profiles.
From backend/ with activated venv: python ../scripts/seed_demo.py
"""
import json
import sys
from pathlib import Path
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Applicant, Policy  # noqa: E402
from app.main import _add_version  # noqa: E402

NAMES = {
    "student_aid": "Student Advancement Support Scheme",
    "fellowship": "Regional Skills Fellowship",
    "research_grant": "Community Research Grant",
    "contradictory": "Experimental Merit Award",
}


def main():
    init_db()
    added_policies = added_profiles = 0
    with SessionLocal() as db:
        for slug, name in NAMES.items():
            if db.scalar(select(Policy).where(Policy.name == name)):
                continue
            policy = Policy(name=name)
            db.add(policy)
            db.flush()
            paths = []
            try:
                for version, label in (("old", "Previous / 2026"), ("new", "Updated / 2026")):
                    filename = f"{slug}_{version}.pdf"
                    _, path = _add_version(db, policy, label, filename, (ROOT / "samples" / filename).read_bytes())
                    paths.append(path)
                db.commit()
                added_policies += 1
            except Exception:
                db.rollback()
                for path in paths:
                    path.unlink(missing_ok=True)
                raise
        profiles = json.loads((ROOT / "samples" / "demo_applicants.json").read_text(encoding="utf-8"))
        for entry in profiles:
            if db.scalar(select(Applicant).where(Applicant.name == entry["name"])):
                continue
            db.add(Applicant(name=entry["name"], details=entry["details"]))
            added_profiles += 1
        db.commit()
    print(f"Demo seeded: {added_policies} policy families (8 PDFs), {added_profiles} applicant profiles.")
    print("Visit http://127.0.0.1:5173 and open Compare & simulate.")


if __name__ == "__main__":
    main()
