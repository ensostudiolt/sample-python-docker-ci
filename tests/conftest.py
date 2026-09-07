import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from orderdesk import db
from orderdesk.api import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    db.init_db()
    yield
    db.Base.metadata.drop_all(db.engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    with db.engine.begin() as conn:
        conn.execute(text("TRUNCATE orders RESTART IDENTITY"))
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
