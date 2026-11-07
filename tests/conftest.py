import shutil
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from database import db
from seed import seed_database

@pytest.fixture(scope='session')
def seeded_db(tmp_path_factory):
    path = tmp_path_factory.mktemp('seed') / 'seed.db'
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{path}'})
    with app.app_context():
        db.create_all()
        seed_database('http://127.0.0.1:5001')
        db.session.remove()
        db.engine.dispose()
    return path

@pytest.fixture
def app(tmp_path, seeded_db):
    path = tmp_path / 'test.db'
    shutil.copy2(seeded_db, path)
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{path}'})
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()

@pytest.fixture
def client(app):
    return app.test_client()
