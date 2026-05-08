# tests/test_health.py
import pytest
from app import create_app


@pytest.fixture
def client():
    """
    Creates a test client for our Flask app.
    A fixture runs before each test and provides it with what it needs.
    """
    app = create_app("testing")
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Health endpoint should return 200 with status ok."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["project"] == "Darak"
