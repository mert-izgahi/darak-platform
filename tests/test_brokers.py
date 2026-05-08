# tests/test_brokers.py
import pytest
from app import create_app
from app.auth.models import User
from app.brokers.models import BrokerProfile


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client
    BrokerProfile.objects.delete()
    User.objects.delete()


@pytest.fixture
def auth_token(client):
    """Register a user and return their JWT token."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "phone": "0501234567",
            "password": "password123",
        },
    )
    return response.get_json()["access_token"]


@pytest.fixture
def created_profile(client, auth_token):
    """Create a profile and return the response data."""
    response = client.post(
        "/brokers/profile",
        json={
            "display_name": "Ahmed Ali",
            "bio": "Experienced broker in Damascus",
            "whatsapp_number": "0501234567",
            "city": "Damascus",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    return response.get_json()


# ── Create profile tests ─────────────────────────────────


def test_create_profile_success(client, auth_token):
    response = client.post(
        "/brokers/profile",
        json={"display_name": "Ahmed Ali", "city": "Damascus"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    data = response.get_json()

    assert response.status_code == 201
    assert data["profile"]["display_name"] == "Ahmed Ali"
    assert data["profile"]["slug"] == "ahmed-ali"


def test_create_profile_duplicate(client, auth_token, created_profile):
    response = client.post(
        "/brokers/profile",
        json={"display_name": "Ahmed Ali"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 409


def test_create_profile_no_auth(client):
    response = client.post("/brokers/profile", json={"display_name": "Ahmed Ali"})
    assert response.status_code == 401


# ── Get my profile tests ─────────────────────────────────


def test_get_my_profile(client, auth_token, created_profile):
    response = client.get(
        "/brokers/profile/me", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.get_json()["display_name"] == "Ahmed Ali"


# ── Update profile tests ─────────────────────────────────


def test_update_profile(client, auth_token, created_profile):
    response = client.put(
        "/brokers/profile/me",
        json={"city": "Aleppo", "bio": "Updated bio"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["profile"]["city"] == "Aleppo"
    assert data["profile"]["bio"] == "Updated bio"


# ── Public profile tests ─────────────────────────────────


def test_get_public_profile(client, auth_token, created_profile):
    slug = created_profile["profile"]["slug"]
    response = client.get(f"/brokers/{slug}")

    data = response.get_json()
    assert response.status_code == 200
    assert data["display_name"] == "Ahmed Ali"
    # private fields must not be exposed
    assert "user_id" not in data


def test_get_public_profile_not_found(client):
    response = client.get("/brokers/nonexistent-broker")
    assert response.status_code == 404
