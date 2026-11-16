"""Local-only FastAPI application; start with --host 127.0.0.1."""
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import get_db, init_db
from .eligibility import simulate
from .matching import clause_dict, rule_dict
from .models import Applicant, Clause, Policy, PolicyVersion, Rule
from .nlp import extract_document_rules
from .pdf_service import document_sha256, parse_pdf, render_page
from .report import make_report
from .schemas import ApplicantInput, RuleInput, RulePatch, SimulationInput


@asynccontextmanager
async def lifespan(_app):
    init_db()
    (settings.data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="RuleShift API", version="1.0.0", lifespan=lifespan,
              description="Evidence-grounded local PDF policy analysis. Informational, never official.")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])


@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    """Do not let an unrelated website modify the loopback-only workspace."""
    accepted_origins = {settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173",
                        "http://127.0.0.1:8000", "http://localhost:8000"}
    origin = request.headers.get("origin")
    if request.method in {"POST", "PATCH", "DELETE", "PUT"} and origin and origin not in accepted_origins:
        return JSONResponse({"detail": "Cross-origin modifications are not allowed"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response


DB = Annotated[Session, Depends(get_db)]


def _version(db: Session, version_id: int) -> PolicyVersion:
    obj = db.scalar(select(PolicyVersion).options(selectinload(PolicyVersion.clauses), selectinload(PolicyVersion.rules)).where(PolicyVersion.id == version_id))
    if not obj:
        raise HTTPException(404, "Policy version not found")
    return obj


def _policy(db: Session, policy_id: int) -> Policy:
    obj = db.scalar(select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id))
    if not obj:
        raise HTTPException(404, "Policy not found")
    return obj


def _applicant(db: Session, id_: int) -> Applicant:
    obj = db.get(Applicant, id_)
    if not obj:
        raise HTTPException(404, "Applicant not found")
    return obj


def _policy_out(obj: Policy) -> dict:
    return {"id": obj.id, "name": obj.name, "created_at": obj.created_at,
            "versions": [{"id": v.id, "label": v.label, "created_at": v.created_at, "page_count": v.page_count,
                          "filename": v.original_filename} for v in obj.versions]}


def _warnings(v: PolicyVersion) -> list[dict]:
    # A reviewed manual correction resolves the original extraction warning for its clause.
    reviewed = {r.clause.ordinal for r in v.rules if r.manual and r.status == "accepted" and r.clause is not None}
    return [w for w in v.warnings if w.get("clause") not in reviewed or w.get("kind") == "scan"]


def _version_out(v: PolicyVersion) -> dict:
    return {"id": v.id, "policy_id": v.policy_id, "label": v.label, "filename": v.original_filename,
            "sha256": v.sha256, "page_count": v.page_count, "created_at": v.created_at,
            "warnings": _warnings(v), "clauses": [clause_dict(c) for c in v.clauses],
            "rules": [rule_dict(r) for r in sorted(v.rules, key=lambda r: (r.clause_id, r.id))]}


async def _read_pdf(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Select a .pdf file")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"PDF exceeds {settings.max_upload_mb} MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(422, "Uploaded file is not a PDF")
    return data


def _add_version(db: Session, policy: Policy, label: str, filename: str, data: bytes) -> tuple[PolicyVersion, Path]:
    try:
        clauses, page_count, warnings = parse_pdf(data, max_pages=settings.max_pdf_pages)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    extracted, rule_warnings = extract_document_rules(clauses)
    safe_filename = filename.replace("\\", "/").split("/")[-1][:255]
    stored = uuid.uuid4().hex + ".pdf"
    target = settings.data_dir / "uploads" / stored
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    try:
        version = PolicyVersion(policy=policy, label=label.strip(), original_filename=safe_filename, stored_filename=stored,
                                sha256=document_sha256(data), page_count=page_count, warnings=warnings + rule_warnings)
        db.add(version)
        db.flush()
        mapping = {}
        for parsed in clauses:
            c = Clause(version=version, ordinal=parsed.ordinal, clause_key=parsed.key, heading=parsed.heading,
                       text=parsed.text, page=parsed.page)
            db.add(c)
            db.flush()
            mapping[parsed.ordinal] = c
        for ordinal, row in extracted:
            db.add(Rule(version=version, clause=mapping[ordinal], **row))
        db.flush()
        return version, target
    except Exception:
        target.unlink(missing_ok=True)
        raise


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local", "version": "1.0.0"}


@app.get("/api/dashboard")
def dashboard(db: DB):
    policies = db.scalars(select(Policy).options(selectinload(Policy.versions)).order_by(Policy.created_at.desc()).limit(6)).all()
    return {"policies": db.scalar(select(func.count(Policy.id))),
            "versions": db.scalar(select(func.count(PolicyVersion.id))),
            "applicants": db.scalar(select(func.count(Applicant.id))),
            "rules": db.scalar(select(func.count(Rule.id)).where(Rule.status == "accepted")),
            "recent": [_policy_out(p) for p in policies]}


@app.post("/api/policies/upload-pair", status_code=201)
async def upload_pair(db: DB, name: Annotated[str, Form(min_length=2, max_length=180)],
                      old_file: Annotated[UploadFile, File()], new_file: Annotated[UploadFile, File()],
                      old_label: Annotated[str, Form(min_length=1, max_length=100)] = "Previous",
                      new_label: Annotated[str, Form(min_length=1, max_length=100)] = "Updated"):
    old_data, new_data = await _read_pdf(old_file), await _read_pdf(new_file)
    policy = Policy(name=name.strip())
    saved = []
    try:
        db.add(policy); db.flush()
        old, file_a = _add_version(db, policy, old_label, old_file.filename, old_data)
        saved.append(file_a)
        new, file_b = _add_version(db, policy, new_label, new_file.filename, new_data)
        saved.append(file_b)
        db.commit()
        db.refresh(policy)
        return {"policy": _policy_out(_policy(db, policy.id)), "old_version_id": old.id, "new_version_id": new.id}
    except Exception:
        db.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise


@app.post("/api/policies/{policy_id}/versions", status_code=201)
async def add_policy_version(policy_id: int, db: DB, file: Annotated[UploadFile, File()],
                             label: Annotated[str, Form(min_length=1, max_length=100)]):
    policy = _policy(db, policy_id)
    data = await _read_pdf(file)
    target = None
    try:
        v, target = _add_version(db, policy, label, file.filename, data)
        db.commit()
        return _version_out(_version(db, v.id))
    except Exception:
        db.rollback()
        if target:
            target.unlink(missing_ok=True)
        raise


@app.get("/api/policies")
def list_policies(db: DB, search: str = Query(default="", max_length=150)):
    q = select(Policy).options(selectinload(Policy.versions)).order_by(Policy.created_at.desc())
    if search.strip():
        q = q.where(Policy.name.ilike("%" + search.strip() + "%"))
    return [_policy_out(obj) for obj in db.scalars(q).all()]


@app.get("/api/policies/{policy_id}")
def get_policy(policy_id: int, db: DB):
    return _policy_out(_policy(db, policy_id))


@app.delete("/api/policies/{policy_id}", status_code=204)
def delete_policy(policy_id: int, db: DB):
    policy = _policy(db, policy_id)
    paths = [settings.data_dir / "uploads" / v.stored_filename for v in policy.versions]
    db.delete(policy)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
    return Response(status_code=204)


@app.get("/api/versions/{version_id}")
def get_version(version_id: int, db: DB):
    return _version_out(_version(db, version_id))


@app.get("/api/versions/{version_id}/pages/{page_number}/image")
def page_image(version_id: int, page_number: int, db: DB, clause_id: int | None = None):
    version = _version(db, version_id)
    clause = next((c for c in version.clauses if c.id == clause_id and c.page == page_number), None)
    evidence = clause.text if clause else None
    if page_number < 1 or page_number > version.page_count:
        raise HTTPException(404, "Page not found")
    path = settings.data_dir / "uploads" / version.stored_filename
    if not path.is_file():
        raise HTTPException(404, "PDF file is no longer available")
    try:
        image = render_page(path, page_number, evidence)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(content=image, media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.post("/api/versions/{version_id}/clauses/{clause_id}/rules", status_code=201)
def add_rule(version_id: int, clause_id: int, payload: RuleInput, db: DB):
    version = _version(db, version_id)
    clause = next((c for c in version.clauses if c.id == clause_id), None)
    if clause is None:
        raise HTTPException(404, "Clause not found in this version")
    if _normalize(payload.evidence_text) not in _normalize(clause.text):
        raise HTTPException(422, "Evidence quote must appear exactly in this clause")
    rule = Rule(version=version, clause=clause, page=clause.page, confidence=1.0, manual=True, **payload.model_dump())
    db.add(rule); db.commit(); db.refresh(rule)
    return rule_dict(rule)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


@app.patch("/api/rules/{rule_id}")
def update_rule(rule_id: int, payload: RulePatch, db: DB):
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    if _normalize(payload.evidence_text) not in _normalize(rule.clause.text):
        raise HTTPException(422, "Evidence quote must appear exactly in the source clause")
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    rule.manual = True
    rule.confidence = 1.0
    db.commit()
    return rule_dict(rule)


@app.delete("/api/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: DB):
    rule = db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule); db.commit()
    return Response(status_code=204)


@app.get("/api/applicants")
def list_applicants(db: DB):
    return [_applicant_out(p) for p in db.scalars(select(Applicant).order_by(Applicant.updated_at.desc())).all()]


def _applicant_out(obj: Applicant):
    return {"id": obj.id, "name": obj.name, "details": obj.details,
            "created_at": obj.created_at, "updated_at": obj.updated_at}


@app.post("/api/applicants", status_code=201)
def create_applicant(payload: ApplicantInput, db: DB):
    obj = Applicant(name=payload.name.strip(), details=payload.details.model_dump(mode="json"))
    db.add(obj); db.commit(); db.refresh(obj)
    return _applicant_out(obj)


@app.patch("/api/applicants/{applicant_id}")
def update_applicant(applicant_id: int, payload: ApplicantInput, db: DB):
    obj = _applicant(db, applicant_id)
    obj.name = payload.name.strip()
    obj.details = payload.details.model_dump(mode="json")
    db.commit(); db.refresh(obj)
    return _applicant_out(obj)


@app.delete("/api/applicants/{applicant_id}", status_code=204)
def delete_applicant(applicant_id: int, db: DB):
    db.delete(_applicant(db, applicant_id)); db.commit()
    return Response(status_code=204)


def _simulate(db: Session, old_id: int, new_id: int, applicant_id: int):
    old = _version(db, old_id); new = _version(db, new_id)
    applicant = _applicant(db, applicant_id)
    # Exclude original extraction warnings once a clause was manually reviewed.
    old.warnings = _warnings(old)
    new.warnings = _warnings(new)
    try:
        result = simulate(old, new, applicant.details)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result.update({"policy_name": old.policy.name, "applicant_name": applicant.name,
                   "applicant_id": applicant.id, "old_label": old.label, "new_label": new.label,
                   "old_version_id": old.id, "new_version_id": new.id})
    return result


@app.post("/api/simulations")
def simulations(payload: SimulationInput, db: DB):
    return _simulate(db, payload.old_version_id, payload.new_version_id, payload.applicant_id)


@app.get("/api/reports/comparison.pdf")
def report(old_version_id: int, new_version_id: int, applicant_id: int, db: DB):
    result = _simulate(db, old_version_id, new_version_id, applicant_id)
    pdf = make_report(result["policy_name"], result["old_label"], result["new_label"], result["applicant_name"], result)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="RuleShift-comparison.pdf"',
                             "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
