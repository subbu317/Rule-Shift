from io import BytesIO
from pathlib import Path


def test_health_dashboard_empty(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    assert client.get('/api/dashboard').json()['policies'] == 0


def test_upload_persists_versions_rules_and_history(client, uploaded):
    policy = uploaded['policy']
    assert len(policy['versions']) == 2
    assert client.get('/api/dashboard').json()['rules'] == 14
    assert client.get('/api/policies?search=Student').json()[0]['id'] == policy['id']
    detail = client.get(f"/api/versions/{uploaded['old_version_id']}").json()
    assert detail['clauses'][0]['page'] == 1
    assert detail['rules'][0]['evidence_text'].startswith('1. Age')


def test_evaluate_export_and_view_evidence(client, uploaded, applicant):
    payload = {'old_version_id': uploaded['old_version_id'], 'new_version_id': uploaded['new_version_id'], 'applicant_id': applicant['id']}
    response = client.post('/api/simulations', json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['before']['status'] == 'eligible'
    assert result['after']['status'] == 'ineligible'
    assert result['eligibility_changed']
    assert any(x['field'] == 'marks' for x in result['applicant_impacts'])
    exported = client.get('/api/reports/comparison.pdf', params=payload)
    assert exported.status_code == 200 and exported.content.startswith(b'%PDF-')
    assert exported.headers['content-type'] == 'application/pdf'
    version = client.get(f"/api/versions/{uploaded['old_version_id']}").json()
    clause_id = version['clauses'][0]['id']
    image = client.get(f"/api/versions/{uploaded['old_version_id']}/pages/1/image?clause_id={clause_id}")
    assert image.status_code == 200 and image.content.startswith(b'\x89PNG')


def test_manual_edit_rule_changes_simulation(client, uploaded, applicant):
    version = client.get(f"/api/versions/{uploaded['new_version_id']}").json()
    marks_rule = next(x for x in version['rules'] if x['field'] == 'marks')
    changed = {k: marks_rule[k] for k in ('field', 'operator', 'value', 'evidence_text', 'status', 'reviewer_note')}
    changed['value'] = {'number': 60.0}
    changed['reviewer_note'] = 'Synthetic experiment; source remains visible.'
    response = client.patch(f"/api/rules/{marks_rule['id']}", json=changed)
    assert response.status_code == 200, response.text
    assert response.json()['manual'] is True
    before = client.post('/api/simulations', json={'old_version_id': uploaded['old_version_id'], 'new_version_id': uploaded['new_version_id'], 'applicant_id': applicant['id']}).json()
    # Residence proof is still missing; a separately amended document rule continues to fail.
    assert before['after']['status'] == 'ineligible'
    assert not any(x['field'] == 'marks' for x in before['applicant_impacts'])


def test_manual_create_rule_and_delete(client, uploaded):
    version = client.get(f"/api/versions/{uploaded['new_version_id']}").json()
    clause = version['clauses'][0]
    rule = {'field': 'age', 'operator': 'between', 'value': {'min': 18, 'max': 27, 'as_of': '2026-07-01'},
            'evidence_text': clause['text'], 'status': 'accepted', 'reviewer_note': 'Manual proofread'}
    created = client.post(f"/api/versions/{version['id']}/clauses/{clause['id']}/rules", json=rule)
    assert created.status_code == 201, created.text
    rid = created.json()['id']
    assert created.json()['manual']
    assert client.delete(f'/api/rules/{rid}').status_code == 204
    assert client.patch(f'/api/rules/{rid}', json=rule).status_code == 404


def test_non_evidence_rule_is_rejected(client, uploaded):
    version = client.get(f"/api/versions/{uploaded['new_version_id']}").json()
    c = version['clauses'][0]
    r = {'field': 'age', 'operator': 'between', 'value': {'min': 18, 'max': 27, 'as_of': '2026-07-01'},
         'evidence_text': 'An imaginary requirement that is absent from the PDF', 'status': 'accepted', 'reviewer_note': ''}
    assert client.post(f"/api/versions/{version['id']}/clauses/{c['id']}/rules", json=r).status_code == 422


def test_invalid_pdf_and_profile(client, sample_data):
    result = client.post('/api/policies/upload-pair', data={'name': 'Bad PDF'},
                         files={'old_file': ('old.pdf', b'not pdf', 'application/pdf'),
                                'new_file': ('new.pdf', sample_data('student_aid_new.pdf'), 'application/pdf')})
    assert result.status_code == 422
    assert client.get('/api/dashboard').json()['policies'] == 0
    result = client.post('/api/applicants', json={'name': 'Bad', 'details': {'marks': 150}})
    assert result.status_code == 422


def test_different_policy_family_rejected(client, uploaded, applicant, sample_data):
    second = client.post('/api/policies/upload-pair', data={'name': 'Another policy'}, files={
        'old_file': ('fellow_old.pdf', sample_data('fellowship_old.pdf'), 'application/pdf'),
        'new_file': ('fellow_new.pdf', sample_data('fellowship_new.pdf'), 'application/pdf')}).json()
    result = client.post('/api/simulations', json={'old_version_id': uploaded['old_version_id'],
                                                  'new_version_id': second['new_version_id'], 'applicant_id': applicant['id']})
    assert result.status_code == 422


def test_delete_cascades_and_removes_pdfs(client, uploaded, applicant, tmp_path):
    path = tmp_path / 'uploads'
    assert len(list(path.glob('*.pdf'))) == 2
    assert client.delete(f"/api/policies/{uploaded['policy']['id']}").status_code == 204
    assert list(path.glob('*.pdf')) == []
    assert client.get('/api/dashboard').json()['rules'] == 0
    assert client.delete(f"/api/applicants/{applicant['id']}").status_code == 204
    assert client.get('/api/applicants').json() == []


def test_profile_update_and_search(client, applicant):
    updated = client.patch(f"/api/applicants/{applicant['id']}", json={'name': 'Updated', 'details': {'marks': 90}})
    assert updated.status_code == 200
    assert updated.json()['details']['date_of_birth'] is None
    assert client.get('/api/applicants').json()[0]['name'] == 'Updated'


def test_cross_origin_mutation_is_blocked_and_private_responses_uncached(client):
    response = client.post('/api/applicants', headers={'Origin': 'https://malicious.example'},
                           json={'name': 'Blocked', 'details': {}})
    assert response.status_code == 403
    private = client.get('/api/applicants')
    assert private.headers['cache-control'] == 'no-store'
    assert private.headers['x-content-type-options'] == 'nosniff'
