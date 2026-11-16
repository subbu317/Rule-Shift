"""Explainable counterfactual eligibility engine.
Outputs are conditional on extracted/reviewed passages, never official determinations.
"""
from datetime import date
from collections import defaultdict

RANKS = {"class10": 1, "class12": 2, "diploma": 2, "bachelor": 3, "master": 4, "doctorate": 5}
PROFILE_KEYS = {"age": "date_of_birth", "education_level": "education_level", "marks": "marks",
                "annual_income": "annual_income", "category": "category", "application_date": "application_date", "documents": "documents"}


def _date(value):
    if value is None:
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _age(dob, as_of):
    return as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))


def _result(rule, status, detail):
    return {"rule_id": rule.id, "clause_id": rule.clause_id, "field": rule.field, "operator": rule.operator,
            "threshold": rule.value, "status": status, "detail": detail, "page": rule.page, "evidence_text": rule.evidence_text}


def detect_conflicts(rules: list) -> list[dict]:
    fields = defaultdict(list)
    for r in rules:
        if r.status == "accepted":
            fields[r.field].append(r)
    errors = []
    for field in ("marks", "annual_income"):
        mins = [r.value["number"] for r in fields[field] if r.operator == "min"]
        maxs = [r.value["number"] for r in fields[field] if r.operator == "max"]
        if mins and maxs and max(mins) > min(maxs):
            errors.append({"field": field, "message": f"Conflicting {field} thresholds: minimum exceeds maximum.",
                           "rule_ids": [r.id for r in fields[field]]})
    if len(fields["age"]) > 1:
        low = max(r.value["min"] for r in fields["age"])
        high = min(r.value["max"] for r in fields["age"])
        dates = set(str(r.value.get("as_of")) for r in fields["age"])
        if low > high and len(dates) == 1:
            errors.append({"field": "age", "message": "Age ranges have no intersection.",
                           "rule_ids": [r.id for r in fields["age"]]})
    if len(fields["category"]) > 1:
        allowed = set(fields["category"][0].value["items"])
        for r in fields["category"][1:]:
            allowed.intersection_update(r.value["items"])
        if not allowed:
            errors.append({"field": "category", "message": "Category allowlists have no intersection.",
                           "rule_ids": [r.id for r in fields["category"]]})
    return errors


def evaluate_rule(rule, applicant: dict) -> dict:
    field, val, operator = rule.field, rule.value, rule.operator
    data = applicant.get(PROFILE_KEYS[field])
    if data is None:
        return _result(rule, "undetermined", f"Missing applicant field: {PROFILE_KEYS[field]}")
    try:
        if field == "age":
            if not val.get("as_of"):
                return _result(rule, "undetermined", "Age rule lacks an explicit reference date")
            dob, day = _date(data), _date(val["as_of"])
            if dob > day:
                return _result(rule, "undetermined", "Birth date is after the policy reference date")
            actual = _age(dob, day)
            good = val["min"] <= actual <= val["max"]
            detail = f"Age {actual} on {day.isoformat()}; required {val['min']}–{val['max']}"
        elif field == "education_level":
            actual, required = RANKS.get(data), RANKS.get(val["level"])
            if actual is None or required is None:
                return _result(rule, "undetermined", "Unrecognized qualification level")
            good = actual >= required
            detail = f"Education {data}; minimum {val['level']} (level-only comparison)"
        elif field in ("marks", "annual_income"):
            actual = float(data)
            threshold = float(val["number"])
            good = actual >= threshold if operator == "min" else actual <= threshold
            detail = f"Applicant {field}: {actual:g}; {operator} {threshold:g}"
        elif field == "category":
            good = data in val["items"]
            detail = f"Applicant category {data}; permitted: {', '.join(val['items'])}"
        elif field == "application_date":
            actual, limit = _date(data), _date(val["date"])
            good = actual <= limit
            detail = f"Application date {actual}; deadline {limit}"
        elif field == "documents":
            owned = set(str(x).lower().strip() for x in data)
            required = set(str(x).lower().strip() for x in val["items"])
            missing = sorted(required - owned)
            good = not missing
            detail = "All required documents supplied" if good else "Missing documents: " + ", ".join(missing)
        else:
            return _result(rule, "undetermined", "Unsupported rule field")
        return _result(rule, "pass" if good else "fail", detail)
    except (TypeError, KeyError, ValueError, OverflowError) as exc:
        return _result(rule, "undetermined", f"Could not safely evaluate: {type(exc).__name__}")


def evaluate_version(rules: list, applicant: dict, warnings: list[dict] | None = None) -> dict:
    warnings = warnings or []
    accepted = [r for r in rules if r.status == "accepted"]
    pending = [r for r in rules if r.status == "pending"]
    conflicts = detect_conflicts(rules)
    evaluations = [evaluate_rule(r, applicant) for r in accepted]
    evaluations.extend(_result(r, "undetermined", "Rule requires manual review") for r in pending)
    unknown_warnings = [w for w in warnings if w.get("kind") in ("unparsed", "ambiguous", "scan")]
    reasons = []
    if conflicts:
        reasons.append("Conflicting accepted requirements")
    if pending:
        reasons.append("Rules are awaiting manual review")
    if unknown_warnings:
        reasons.append("Potential unparsed or unreadable requirements")
    if any(e["status"] == "undetermined" for e in evaluations):
        reasons.append("Missing or incomplete applicant inputs")
    if not accepted:
        reasons.append("No verified eligibility rules extracted")
    if conflicts:
        status = "undetermined"
    elif any(e["status"] == "fail" for e in evaluations):
        # A proven failing requirement is enough to rule out eligibility unless the policy contradicts itself.
        status = "ineligible"
    elif reasons:
        status = "undetermined"
    else:
        status = "eligible"
    fields = {}
    for field in PROFILE_KEYS:
        subset = [e for e in evaluations if e["field"] == field]
        if not subset:
            fields[field] = "not_applicable"
        elif any(e["status"] == "fail" for e in subset):
            fields[field] = "fail"
        elif any(e["status"] == "undetermined" for e in subset):
            fields[field] = "undetermined"
        else:
            fields[field] = "pass"
    for c in conflicts:
        fields[c["field"]] = "undetermined"
    missing = sorted({PROFILE_KEYS[e["field"]] for e in evaluations
                      if e["status"] == "undetermined" and e["detail"].startswith("Missing applicant")})
    return {"status": status, "rule_checks": evaluations, "field_results": fields,
            "missing_fields": missing, "conflicts": conflicts, "warnings": unknown_warnings,
            "reasons": list(dict.fromkeys(reasons)), "evaluated_rule_count": len(accepted)}


def simulate(old_version, new_version, applicant: dict) -> dict:
    from .matching import compare_clauses
    if old_version.policy_id != new_version.policy_id:
        raise ValueError("Policy versions must belong to the same policy")
    diff = compare_clauses(old_version.clauses, new_version.clauses, old_version.rules, new_version.rules)
    before = evaluate_version(old_version.rules, applicant, old_version.warnings)
    after = evaluate_version(new_version.rules, applicant, new_version.warnings)
    impacts = []
    seen = set()
    for change in diff["clauses"]:
        if change["status"] == "unchanged":
            continue
        fields = {r["field"] for r in change["old_rules"] + change["new_rules"] if r["status"] != "rejected"}
        for field in fields:
            previous = before["field_results"][field]
            current = after["field_results"][field]
            if previous == current:
                continue
            key = (field, change["old"]["id"] if change["old"] else None, change["new"]["id"] if change["new"] else None)
            if key in seen:
                continue
            seen.add(key)
            impacts.append({"field": field, "before": previous, "after": current,
                            "change_type": change["status"], "old_clause": change["old"], "new_clause": change["new"],
                            "old_rules": change["old_rules"], "new_rules": change["new_rules"],
                            "decisive": before["status"] != after["status"] and (previous == "fail" or current == "fail" or
                                          (previous == "undetermined" and current == "pass") or
                                          (previous == "pass" and current == "undetermined"))})
    return {"before": before, "after": after, "comparison": diff,
            "eligibility_changed": before["status"] != after["status"],
            "applicant_impacts": impacts,
            "disclaimer": "Informational simulation based on text-extracted and reviewed criteria. Not an official eligibility determination."}
