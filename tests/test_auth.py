# tests/test_auth.py
import pytest
from app import create_app
from app.auth.models import User


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client
    # cleanup — remove all users created during tests
    User.objects.delete()


@pytest.fixture
def registered_user(client):
    """Creates a user and returns their token — reused across tests."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test Broker",
            "email": "broker@test.com",
            "phone": "0501234567",
            "password": "password123",
        },
    )
    return response.get_json()


# ── Register tests ───────────────────────────────────────


def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "phone": "0501234567",
            "password": "password123",
        },
    )
    data = response.get_json()

    assert response.status_code == 201
    assert "access_token" in data
    assert data["user"]["email"] == "ahmed@test.com"


def test_register_duplicate_email(client, registered_user):
    response = client.post(
        "/auth/register",
        json={
            "name": "Another User",
            "email": "broker@test.com",  # same email
            "phone": "0509999999",
            "password": "password123",
        },
    )
    assert response.status_code == 409


def test_register_invalid_data(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "X",  # too short
            "email": "not-an-email",
            "password": "123",  # too short
        },
    )
    assert response.status_code == 400


# ── Login tests ──────────────────────────────────────────


def test_login_success(client, registered_user):
    response = client.post(
        "/auth/login", json={"email": "broker@test.com", "password": "password123"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in data


def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/auth/login", json={"email": "broker@test.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/auth/login", json={"email": "nobody@test.com", "password": "password123"}
    )
    assert response.status_code == 401


# ── Protected route tests ────────────────────────────────


def test_me_authenticated(client, registered_user):
    token = registered_user["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["email"] == "broker@test.com"


def test_me_no_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
