import pytest
from app.pdf_service import ParsedClause, parse_pdf
from app.nlp import extract_rules, extract_document_rules


def test_extract_text_and_page_reference(sample_data):
    clauses, count, warnings = parse_pdf(sample_data('student_aid_old.pdf'))
    assert count == 1
    assert len(clauses) == 8
    assert all(c.page == 1 for c in clauses)
    assert 'between 18 and 25' in clauses[0].text
    assert not warnings


def test_pdf_rejects_non_pdf():
    with pytest.raises(ValueError, match='not a PDF'):
        parse_pdf(b'plain text pretending to be pdf')


def test_pdf_rejects_low_page_limit(sample_data):
    with pytest.raises(ValueError, match='PDF must have'):
        parse_pdf(sample_data('student_aid_old.pdf'), max_pages=0)


def test_all_required_fields_extracted(sample_data):
    clauses, _, _ = parse_pdf(sample_data('student_aid_old.pdf'))
    structured, _ = extract_document_rules(clauses)
    assert {rule['field'] for _, rule in structured} == {'age', 'education_level', 'marks', 'annual_income', 'category', 'application_date', 'documents'}
    assert next(r for _, r in structured if r['field'] == 'annual_income')['value']['number'] == 800000
    assert next(r for _, r in structured if r['field'] == 'application_date')['value']['date'] == '2026-08-31'


def test_income_lakh_explicit_units():
    clause = ParsedClause(1, '1', 'Income', '1. Income: Annual family income must not exceed INR 8 lakh.', 4)
    rules, warnings = extract_rules(clause)
    assert rules[0]['value'] == {'number': 800000}
    assert rules[0]['page'] == 4
    assert warnings == []


def test_age_missing_reference_date_is_pending():
    clause = ParsedClause(1, '1', 'Age', '1. Age: Applicant age must be between 18 and 25 years.', 1)
    rules, warnings = extract_rules(clause)
    assert rules[0]['status'] == 'pending'
    assert warnings[0]['kind'] == 'ambiguous'


def test_specialized_discipline_does_not_become_generic_degree():
    clause = ParsedClause(1, '1', 'Qualification', "1. Qualification: Applicants must hold a Bachelor's degree in engineering.", 2)
    rules, warnings = extract_rules(clause)
    assert rules == []
    assert any(w['kind'] == 'unparsed' for w in warnings)


def test_unknown_experience_rule_is_flagged():
    clause = ParsedClause(1, '1', 'Experience', '1. Experience: Applicant must have at least 3 years experience.', 2)
    rules, warnings = extract_rules(clause)
    assert not rules and warnings[0]['kind'] == 'unparsed'


def test_explicit_categories_only():
    explicit = ParsedClause(1, '1', 'Category', '1. Category: Only applicants in OBC, SC and EWS categories may apply.', 1)
    incidental = ParsedClause(1, '1', 'Category', '1. Category: General, SC and EWS categories are discussed in appendix.', 1)
    assert extract_rules(explicit)[0][0]['value']['items'] == ['OBC', 'SC', 'EWS']
    assert extract_rules(incidental)[0] == []


def test_exception_language_forces_manual_review():
    clause = ParsedClause(1, '1', 'Marks', '1. Marks: Applicants must have at least 60% marks, unless exempted by the district office.', 2)
    rules, warnings = extract_rules(clause)
    assert rules[0]['field'] == 'marks'
    assert rules[0]['status'] == 'pending'
    assert any(w['kind'] == 'ambiguous' for w in warnings)


def test_supported_rule_does_not_hide_unparsed_extra_condition():
    clause = ParsedClause(1, '1', 'Experience and marks', '1. Eligibility: Applicants must have at least 60% marks and must have 2 years experience.', 2)
    rules, warnings = extract_rules(clause)
    assert rules[0]['field'] == 'marks'
    assert any(w['kind'] == 'unparsed' for w in warnings)
