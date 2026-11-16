from types import SimpleNamespace
from app.eligibility import detect_conflicts, evaluate_version, simulate
from app.matching import compare_clauses
from app.nlp import extract_document_rules
from app.pdf_service import parse_pdf


def rule(id, field, operator, value, status='accepted', clause_id=1):
    return SimpleNamespace(id=id, clause_id=clause_id, field=field, operator=operator, value=value,
                           status=status, page=1, evidence_text='source passage', manual=False, reviewer_note='', confidence=.9)


def test_match_added_removed_and_modified(sample_data):
    old_p, _, _ = parse_pdf(sample_data('student_aid_old.pdf'))
    new_p, _, _ = parse_pdf(sample_data('student_aid_new.pdf'))
    o = [SimpleNamespace(**vars(c), clause_key=c.key, id=100+i) for i, c in enumerate(old_p)]
    n = [SimpleNamespace(**vars(c), clause_key=c.key, id=200+i) for i, c in enumerate(new_p)]
    result = compare_clauses(o, n)
    assert result['counts']['modified'] >= 5
    assert result['counts']['unchanged'] >= 2
    assert any(x['old'] and '60%' in x['old']['text'] and x['new'] and '65%' in x['new']['text'] for x in result['clauses'])


def test_added_clause_detected():
    a = SimpleNamespace(id=1, ordinal=1, clause_key='1', heading='Age', text='Age must be between 20 and 30 years', page=1)
    b = SimpleNamespace(id=2, ordinal=2, clause_key='2', heading='Income', text='Income must not exceed INR 800000', page=1)
    c = SimpleNamespace(id=3, ordinal=1, clause_key='1', heading='Age', text='Age must be between 20 and 30 years', page=1)
    result = compare_clauses([a], [c, b])
    assert result['counts']['added'] == 1


def test_birthdate_age_boundary():
    r = rule(1, 'age', 'between', {'min': 18, 'max': 25, 'as_of': '2026-07-01'})
    assert evaluate_version([r], {'date_of_birth': '2001-07-01'})['status'] == 'eligible'
    assert evaluate_version([r], {'date_of_birth': '2000-06-30'})['status'] == 'ineligible'


def test_missing_information_undetermined():
    r = rule(1, 'marks', 'min', {'number': 65})
    result = evaluate_version([r], {'marks': None})
    assert result['status'] == 'undetermined'
    assert result['missing_fields'] == ['marks']


def test_failure_is_deterministic_even_if_other_field_missing():
    rules = [rule(1, 'marks', 'min', {'number': 65}), rule(2, 'annual_income', 'max', {'number': 800000})]
    assert evaluate_version(rules, {'marks': 60})['status'] == 'ineligible'


def test_conflicting_requirements_never_force_binary_decision():
    rules = [rule(1, 'marks', 'min', {'number': 80}), rule(2, 'marks', 'max', {'number': 70})]
    assert detect_conflicts(rules)[0]['field'] == 'marks'
    result = evaluate_version(rules, {'marks': 100})
    assert result['status'] == 'undetermined'
    assert result['conflicts']


def test_disjoint_category_whitelists():
    rules = [rule(1, 'category', 'in', {'items': ['SC']}), rule(2, 'category', 'in', {'items': ['General']})]
    assert evaluate_version(rules, {'category': 'SC'})['status'] == 'undetermined'


def test_pending_and_unparsed_requirements():
    r = rule(1, 'marks', 'min', {'number': 60}, status='pending')
    assert evaluate_version([r], {'marks': 88})['status'] == 'undetermined'
    w = [{'page': 2, 'kind': 'unparsed', 'message': 'manual review'}]
    assert evaluate_version([rule(2, 'marks', 'min', {'number': 60})], {'marks': 88}, w)['status'] == 'undetermined'


def test_documents_require_all_explicit_items():
    r = rule(1, 'documents', 'all_of', {'items': ['identity proof', 'degree certificate']})
    assert evaluate_version([r], {'documents': ['degree certificate']})['status'] == 'ineligible'
    assert evaluate_version([r], {'documents': ['identity proof', 'degree certificate']})['status'] == 'eligible'


def test_fellowship_change_grounds_impact(sample_data):
    from scripts import evaluate as evaluation
    old = evaluation.make_version(sample_data('fellowship_old.pdf'), 1)
    new = evaluation.make_version(sample_data('fellowship_new.pdf'), 2)
    applicant = {'date_of_birth': '1995-05-01', 'education_level': 'master', 'marks': 76, 'annual_income': 600000,
                 'application_date': '2026-05-15', 'documents': ['identity proof', 'degree certificate']}
    output = simulate(old, new, applicant)
    assert output['before']['status'] == 'ineligible'
    assert output['after']['status'] == 'eligible'
    assert {i['field'] for i in output['applicant_impacts']} >= {'age', 'application_date'}
    assert all(i['new_clause']['page'] == 1 for i in output['applicant_impacts'] if i['new_clause'])
