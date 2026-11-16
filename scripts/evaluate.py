"""Reproducible measurements on labeled, synthetic PDF policies.
Baseline: raw extracted-text inequality => predicts *everyone* impacted by a changed PDF.
RuleShift: deterministic structured extraction + applicant-specific counterfactual.
Baseline has no eligibility decision capability (coverage zero, accuracy N/A).
"""
import json
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.eligibility import simulate  # noqa: E402
from app.nlp import extract_document_rules  # noqa: E402
from app.pdf_service import parse_pdf  # noqa: E402


def baseline(old: bytes, new: bytes) -> bool:
    def extract(data):
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            return "\n".join(p.get_text("text") for p in pdf)
    return extract(old) != extract(new)


def make_version(data: bytes, version_id: int) -> SimpleNamespace:
    parsed, _pages, warnings = parse_pdf(data)
    rule_rows, flagged = extract_document_rules(parsed)
    clauses = [SimpleNamespace(**{**vars(c), "clause_key": c.key}, id=version_id * 1000 + c.ordinal) for c in parsed]
    by_ord = {c.ordinal: c for c in clauses}
    rules = [SimpleNamespace(**row, id=version_id * 10000 + number,
                             clause_id=by_ord[ordinal].id, manual=False, reviewer_note="")
             for number, (ordinal, row) in enumerate(rule_rows, start=1)]
    return SimpleNamespace(id=version_id, policy_id=1, clauses=clauses, rules=rules, warnings=warnings + flagged)


def calculate_stats(gold: list[bool], predicted: list[bool]):
    tp = sum(a and b for a, b in zip(gold, predicted))
    fp = sum(not a and b for a, b in zip(gold, predicted))
    fn = sum(a and not b for a, b in zip(gold, predicted))
    tn = len(gold) - tp - fp - fn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(tp / (tp + fp), 4) if tp + fp else 0,
            "recall": round(tp / (tp + fn), 4) if tp + fn else 0}


def evaluate(repeats=3):
    all_cases = json.loads((ROOT / "samples/evaluation_cases.json").read_text(encoding="utf-8"))["cases"]
    gold, baseline_prediction, structured_prediction = [], [], []
    baseline_durations, structured_durations = [], []
    decisions_expected = decisions_correct = 0
    cases_out = []
    for case in all_cases:
        old = (ROOT / "samples" / (case["policy"] + "_old.pdf")).read_bytes()
        new = (ROOT / "samples" / (case["policy"] + "_new.pdf")).read_bytes()
        b_value = None
        r_value = None
        for _ in range(repeats):
            start = time.perf_counter_ns()
            b_value = baseline(old, new)
            baseline_durations.append((time.perf_counter_ns() - start) / 1e6)
            start = time.perf_counter_ns()
            old_v = make_version(old, 1)
            new_v = make_version(new, 2)
            r_value = simulate(old_v, new_v, case["applicant"]["details"])
            structured_durations.append((time.perf_counter_ns() - start) / 1e6)
        expected = case["before"] != case["after"]
        predicted = r_value["eligibility_changed"]
        gold.append(expected)
        baseline_prediction.append(b_value)
        structured_prediction.append(predicted)
        for side, truth in (("before", case["before"]), ("after", case["after"])):
            decisions_expected += 1
            decisions_correct += int(r_value[side]["status"] == truth)
        cases_out.append({"policy": case["policy"], "applicant": case["applicant"]["name"],
                          "expected_before": case["before"], "actual_before": r_value["before"]["status"],
                          "expected_after": case["after"], "actual_after": r_value["after"]["status"],
                          "expected_change": expected, "predicted_change": predicted})
    result = {
        "dataset": "Synthetic, hand-labeled policy/applicant cases; no real applicants or government documents",
        "cases": len(all_cases), "decisions": decisions_expected,
        "measurement": f"Median across {repeats} warm/cold mixed executions per case; includes PDF opening and extraction; single machine",
        "baseline": {"impact_change_detection": calculate_stats(gold, baseline_prediction),
                     "eligibility_decision_accuracy": None, "decision_coverage": 0.0,
                     "median_runtime_ms": round(statistics.median(baseline_durations), 3)},
        "ruleshift": {"impact_change_detection": calculate_stats(gold, structured_prediction),
                      "eligibility_decision_accuracy": round(decisions_correct / decisions_expected, 4),
                      "decision_coverage": 1.0,
                      "median_runtime_ms": round(statistics.median(structured_durations), 3)},
        "cases_detail": cases_out,
    }
    (ROOT / "samples/evaluation_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases_detail"}, indent=2))
    mismatches = [r for r in cases_out if r["expected_before"] != r["actual_before"] or r["expected_after"] != r["actual_after"] or r["expected_change"] != r["predicted_change"]]
    if mismatches:
        print("MISMATCHES", json.dumps(mismatches, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(evaluate())
