import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
import app.main as main_module  # noqa: E402
from app.config import settings  # noqa: E402
from app import models  # noqa: F401,E402

SAMPLES = Path(__file__).resolve().parents[2] / 'samples'


@pytest.fixture
def sample_data():
    return lambda filename: (SAMPLES / filename).read_bytes()


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    monkeypatch.setattr(main_module, 'init_db', lambda: None)

    def db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def uploaded(client, sample_data):
    result = client.post('/api/policies/upload-pair', data={'name': 'Student Support', 'old_label': '2025 rules', 'new_label': '2026 rules'},
                         files={'old_file': ('old.pdf', sample_data('student_aid_old.pdf'), 'application/pdf'),
                                'new_file': ('new.pdf', sample_data('student_aid_new.pdf'), 'application/pdf')})
    assert result.status_code == 201, result.text
    return result.json()


@pytest.fixture
def applicant(client):
    result = client.post('/api/applicants', json={
        'name': 'Asha', 'details': {'date_of_birth': '2003-01-01', 'education_level': 'bachelor',
                                  'marks': 62, 'annual_income': 700000, 'category': 'EWS',
                                  'application_date': '2026-08-15', 'documents': ['identity proof', 'degree certificate', 'income certificate']}
    })
    assert result.status_code == 201
    return result.json()
