# Architecture and correctness contract

## Runtime structure

```text
React/Vite browser UI (127.0.0.1:5173)
          |
          | /api via Vite dev proxy
          v
FastAPI (127.0.0.1:8000)
    |-- SQLAlchemy models -> SQLite (PostgreSQL-compatible mappings)
    |-- PDF parser        -> PyMuPDF embedded text and page rasterization
    |-- Rule extractor    -> deterministic regex/structured thresholds
    |-- Clause matcher    -> RapidFuzz lexical + heading + sequence alignment
    |-- Counterfactual    -> per-rule check, conflicts, uncertainty, impacts
    `-- PDF report        -> ReportLab generated audit artifact
```

The database preserves policy identity and version identity separately. A rule references a clause and a version; every clause records its page. Uploaded files receive a random UUID filename and are stored under a non-public folder.

## Decision contract

Each accepted rule produces `pass`, `fail`, or `undetermined` with `page`, `evidence_text`, and a plain-language comparison. A rejected rule has no effect. Pending rules block a positive eligibility conclusion. A contradiction across accepted criteria produces `undetermined` regardless of profile fields. If a verified constraint fails and the policy has no conflicting accepted constraints, the applicant is `ineligible`. An applicant is `eligible` only when all accepted checks pass and there are no pending, unparsed, unreadable or conflicting requirements. Otherwise the result is `undetermined`.

### Supported rule JSON shapes

```json
{"field":"age","operator":"between","value":{"min":18,"max":25,"as_of":"2026-07-01"}}
{"field":"education_level","operator":"at_least","value":{"level":"bachelor"}}
{"field":"marks","operator":"min","value":{"number":60}}
{"field":"marks","operator":"max","value":{"number":90}}
{"field":"annual_income","operator":"max","value":{"number":800000}}
{"field":"category","operator":"in","value":{"items":["General","OBC","SC","ST","EWS"]}}
{"field":"application_date","operator":"by","value":{"date":"2026-08-31"}}
{"field":"documents","operator":"all_of","value":{"items":["identity proof","degree certificate"]}}
```

Each rule also carries `clause_id`, `version_id`, the original `evidence_text`, `page`, review status, confidence and `manual` flag.

## Evidence and conservative decisions

The extractor is designed to **avoid silent extrapolation**: it emits structured rules only for supported forms, and flags unparsed prescriptive language. Future extraction patterns must have fixtures covering page reference, false positives, missing context and conflicting language. Automated agreement on synthetic cases must not be generalized to regulatory accuracy.

A reviewer may manually override a JSON threshold only while retaining a verbatim quote present in the same clause; manually reviewed values are tagged as such. A human must check that the override is correct. An extracted passage is **not** proof that the system has fully interpreted every exception on that page.

## Baseline definition

The baseline is a *non-applicant-specific* binary classifier: if the extracted text of two PDFs differs, it predicts eligibility change for all applicants. It does not attempt eligibility decisions. RuleShift predicts eligibility-change only when the evaluated before/after statuses differ. Precision/recall are computed on the same hand-labeled synthetic cases. Decision accuracy is calculated for RuleShift only, because inventing baseline decisions would make the comparison misleading.

## Security boundaries

The application intentionally has no public login; both servers must stay bound to loopback. PDFs and applicant profiles are never served as raw public files, but page previews and profile APIs are accessible to local processes. No network transmission to AI services occurs. Sensitive data remains unencrypted at rest. Local host/origin guards and no-store cache headers are defense-in-depth, not a substitute for application authentication in a publicly exposed deployment.
