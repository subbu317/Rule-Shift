"""Evidence-first, deterministic rule extraction. No LLM and no invented constraints."""
import re
from datetime import datetime
from .pdf_service import ParsedClause

_CATEGORIES = ("General", "OBC", "SC", "ST", "EWS")
_LEVELS = {"class 10": "class10", "class 12": "class12", "diploma": "diploma", "bachelor": "bachelor", "master": "master", "doctorate": "doctorate", "phd": "doctorate"}


def _amount(s: str) -> float:
    t = s.lower().replace(",", "").replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if not m:
        raise ValueError("No amount")
    value = float(m.group(1))
    if "crore" in t:
        value *= 10_000_000
    elif "lakh" in t or "lac" in t:
        value *= 100_000
    return value


def _capture_date(s: str) -> str | None:
    hit = re.search(r"\b(20\d\d[-/]\d\d[-/]\d\d)\b", s)
    if hit:
        value = hit.group(1).replace("/", "-")
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None
    hit = re.search(r"\b(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d\d)\b", s, flags=re.I)
    if hit:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(hit.group(1), fmt).date().isoformat()
            except ValueError:
                pass
    return None


def _rule(clause: ParsedClause, field: str, operator: str, value: dict, evidence: str | None = None, status: str = "accepted") -> dict:
    return {"field": field, "operator": operator, "value": value, "evidence_text": evidence or clause.text,
            "page": clause.page, "status": status, "confidence": 0.97 if status == "accepted" else 0.45}


def extract_rules(clause: ParsedClause) -> tuple[list[dict], list[dict]]:
    text = clause.text
    s = re.sub(r"\s+", " ", text)
    lower = s.lower()
    out: list[dict] = []
    warnings: list[dict] = []

    if re.search(r"\b(age|aged|years old)\b", lower) and re.search(r"\b(must|between|from|eligible|years)\b", lower):
        match = re.search(r"\bbetween\s+(\d{1,3})\s+and\s+(\d{1,3})\s+years\b|\b(?:aged?|age)\s+(\d{1,3})\s*(?:to|[-–])\s*(\d{1,3})\b", s, re.I)
        if match:
            low, high = [int(x) for x in (match.group(1, 2) if match.group(1) else match.group(3, 4))]
            as_of_hit = re.search(r"\bas of\s+(.+?)(?:\.|;|$)", s, re.I)
            as_of = _capture_date(as_of_hit.group(1)) if as_of_hit else None
            status = "accepted" if as_of and low <= high else "pending"
            out.append(_rule(clause, "age", "between", {"min": low, "max": high, "as_of": as_of}, status=status))
            if status == "pending":
                warnings.append({"page": clause.page, "clause": clause.ordinal, "kind": "ambiguous", "message": "Age criterion has no parseable reference date or has invalid bounds; needs review."})

    for direction, verb in (("min", r"(?:at least|minimum(?:\s+of)?|not less than)"), ("max", r"(?:at most|maximum(?:\s+of)?|not more than)")):
        matches = re.finditer(rf"\b{verb}\s+(\d+(?:\.\d+)?)\s*%", s, flags=re.I)
        for m in matches:
            if re.search(r"\b(marks?|scores?|percentage|qualifying|grades?)\b", lower):
                out.append(_rule(clause, "marks", direction, {"number": float(m.group(1))}))
    # The trailing phrase may be 'marks of at least 60%' (same pattern catches).

    if "income" in lower:
        m = re.search(r"(?:income\s+)?(?:must\s+)?(?:not exceed|not more than|at most|maximum(?:\s+of)?)\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore)?)", s, re.I)
        if m:
            out.append(_rule(clause, "annual_income", "max", {"number": _amount(m.group(1))}))
        m = re.search(r"(?:income\s+)?(?:must\s+)?(?:at least|minimum(?:\s+of)?|not less than)\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore)?)", s, re.I)
        if m:
            out.append(_rule(clause, "annual_income", "min", {"number": _amount(m.group(1))}))

    if re.search(r"\b(degree|diploma|class\s+(?:10|12)|phd|doctorate)\b", lower):
        if re.search(r"\b(must hold|must possess|must have completed|minimum qualification|required qualification|must have)\b", lower):
            level = next((value for keyword, value in _LEVELS.items() if re.search(r"\b" + re.escape(keyword) + r"\b", lower)), None)
            if level:
                # A specific field/discipline requirement is not safely reducible to degree level.
                if re.search(r"\b(?:in|of)\s+(?:computer science|engineering|medicine|mathematics|physics|commerce)\b", lower):
                    warnings.append({"page": clause.page, "clause": clause.ordinal, "kind": "unparsed", "message": "Specialized discipline condition requires manual extraction."})
                else:
                    out.append(_rule(clause, "education_level", "at_least", {"level": level}))

    if re.search(r"\bonly\s+applicants?\s+in\b", lower) and "categor" in lower:
        piece = re.search(r"\bonly\s+applicants?\s+in\s+(.+?)\s+categor(?:y|ies)\b", s, re.I)
        if piece:
            candidates = [c for c in _CATEGORIES if re.search(r"(?<!\w)" + c + r"(?!\w)", piece.group(1), re.I)]
            if candidates:
                out.append(_rule(clause, "category", "in", {"items": candidates}))

    if re.search(r"\b(application|applications|submission|submit|deadline)\b", lower) and re.search(r"\b(on or before|no later than|deadline|closing date)\b", lower):
        d = _capture_date(s)
        if d:
            out.append(_rule(clause, "application_date", "by", {"date": d}))

    m = re.search(r"\brequired\s+documents?\s*:\s*(.+)", s, re.I)
    if m:
        piece = re.split(r"\.(?:\s|$)", m.group(1))[0]
        documents = [x.strip(" .;").lower() for x in re.split(r",\s*|\s+and\s+", piece, flags=re.I) if x.strip(" .;")]
        if documents and len(documents) <= 30:
            out.append(_rule(clause, "documents", "all_of", {"items": documents}))

    # A supported threshold does not make a compound/exception clause safe to auto-accept.
    if out and re.search(r"\b(unless|except|subject to|provided that|only if|either)\b", lower):
        for item in out:
            item["status"] = "pending"
            item["confidence"] = 0.45
        warnings.append({"page": clause.page, "clause": clause.ordinal, "kind": "ambiguous",
                         "message": "Conditional or exception language may change how these rules apply; manual review required."})
    if out and re.search(r"\b(?:must|shall|required)\b.{0,100}\b(experience|residency|domicile|citizenship)\b", lower):
        warnings.append({"page": clause.page, "clause": clause.ordinal, "kind": "unparsed",
                         "message": "A compound clause also mentions a requirement type that is not automatically evaluated."})

    # Suspicious prescriptive text without a supported extraction is not silently accepted.
    if not out and not warnings and re.search(r"\b(must|shall|required|only applicants|minimum eligibility|eligible applicants)\b", lower):
        if re.search(r"\b(age|years|degree|diploma|qualification|marks|score|income|categor|date|deadline|document|experience|residen|domicile|citizen)\b", lower):
            warnings.append({"page": clause.page, "clause": clause.ordinal, "kind": "unparsed", "message": "Potential eligibility requirement could not be mapped to a safe deterministic rule; manual review required."})
    return out, warnings


def extract_document_rules(clauses: list[ParsedClause]) -> tuple[list[tuple[int, dict]], list[dict]]:
    rules: list[tuple[int, dict]] = []
    warnings: list[dict] = []
    for c in clauses:
        found, flagged = extract_rules(c)
        rules.extend((c.ordinal, rule) for rule in found)
        warnings.extend(flagged)
    return rules, warnings
