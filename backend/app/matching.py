"""Clause alignment combines titles, lexical similarity, and rule types.
Unlike plain line diff, this preserves the identity of rephrased provisions.
"""
import re
from rapidfuzz.fuzz import ratio


def _clean(s: str) -> str:
    s = re.sub(r"^\s*(?:\d+(?:\.\d+)*[.)]?|Section\s+\d+)\s+", "", s, flags=re.I)
    return " ".join(re.findall(r"[\w]+", s.lower()))


def _similarity(a, b):
    atext, btext = _clean(a.text), _clean(b.text)
    aheading, bheading = _clean(a.heading), _clean(b.heading)
    atok, btok = set(atext.split()), set(btext.split())
    overlap = len(atok & btok) / max(1, len(atok | btok))
    heading = ratio(aheading, bheading) / 100
    sequence = ratio(atext, btext) / 100
    score = 0.38 * heading + 0.33 * overlap + 0.29 * sequence
    # Numbering alone is not enough to match; boosts only sufficiently similar text.
    if a.clause_key and a.clause_key == b.clause_key and score >= 0.40:
        score += 0.08
    return min(score, 1.0)


def compare_clauses(old_clauses: list, new_clauses: list, old_rules: list | None = None, new_rules: list | None = None) -> dict:
    old_rules = old_rules or []
    new_rules = new_rules or []
    pairs = sorted(((_similarity(o, n), i, j) for i, o in enumerate(old_clauses) for j, n in enumerate(new_clauses)), reverse=True)
    used_old, used_new = set(), set()
    matches = []
    for score, i, j in pairs:
        if score < 0.47:
            break
        if i not in used_old and j not in used_new:
            used_old.add(i); used_new.add(j)
            o, n = old_clauses[i], new_clauses[j]
            # Changed values are detected even when text changes are subtle.
            key = "unchanged" if _clean(o.text) == _clean(n.text) else "modified"
            orules = [r for r in old_rules if r.clause_id == o.id]
            nrules = [r for r in new_rules if r.clause_id == n.id]
            old_signatures = sorted(f"{r.field}:{r.operator}:{str(r.value)}" for r in orules if r.status != "rejected")
            new_signatures = sorted(f"{r.field}:{r.operator}:{str(r.value)}" for r in nrules if r.status != "rejected")
            if old_signatures != new_signatures:
                key = "modified"
            matches.append({"status": key, "similarity": round(score, 3), "old": clause_dict(o), "new": clause_dict(n),
                            "old_rules": [rule_dict(r) for r in orules], "new_rules": [rule_dict(r) for r in nrules]})
    matches.extend({"status": "removed", "similarity": 0, "old": clause_dict(o), "new": None,
                    "old_rules": [rule_dict(r) for r in old_rules if r.clause_id == o.id], "new_rules": []}
                   for i, o in enumerate(old_clauses) if i not in used_old)
    matches.extend({"status": "added", "similarity": 0, "old": None, "new": clause_dict(n),
                    "old_rules": [], "new_rules": [rule_dict(r) for r in new_rules if r.clause_id == n.id]}
                   for j, n in enumerate(new_clauses) if j not in used_new)
    matches.sort(key=lambda m: (m["new"] or m["old"])["ordinal"])
    counts = {state: sum(x["status"] == state for x in matches) for state in ("added", "removed", "modified", "unchanged")}
    return {"counts": counts, "clauses": matches}


def clause_dict(c) -> dict:
    return {"id": c.id, "ordinal": c.ordinal, "clause_key": c.clause_key, "heading": c.heading, "text": c.text, "page": c.page}


def rule_dict(r) -> dict:
    return {"id": r.id, "clause_id": r.clause_id, "field": r.field, "operator": r.operator, "value": r.value,
            "evidence_text": r.evidence_text, "page": r.page, "status": r.status, "confidence": r.confidence,
            "manual": r.manual, "reviewer_note": r.reviewer_note}
