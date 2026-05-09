# tests/test_leads.py
import pytest
from app import create_app
from app.auth.models import User
from app.brokers.models import BrokerProfile
from app.listings.models import Listing
from app.leads.models import Lead


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client
    Lead.objects.delete()
    Listing.objects.delete()
    BrokerProfile.objects.delete()
    User.objects.delete()


@pytest.fixture
def auth_headers(client):
    """Register broker, create profile, return auth headers."""
    client.post(
        "/auth/register",
        json={
            "name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "phone": "0501234567",
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login", json={"email": "ahmed@test.com", "password": "password123"}
    )
    token = login.get_json()["access_token"]
    client.post(
        "/brokers/profile",
        json={"display_name": "Ahmed Ali", "city": "Damascus"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def listing_id(client, auth_headers):
    """Create a listing and return its ID."""
    response = client.post(
        "/listings/",
        json={
            "title": "Modern Apartment in Damascus",
            "property_type": "apartment",
            "purpose": "sale",
            "price": 75000,
            "city": "Damascus",
        },
        headers=auth_headers,
    )
    return response.get_json()["listing"]["id"]


@pytest.fixture
def submitted_lead(client, listing_id):
    """Submit a lead and return response data."""
    response = client.post(
        f"/leads/{listing_id}",
        json={
            "visitor_name": "Khalid Hassan",
            "visitor_phone": "0551234567",
            "message": "I am interested in this apartment",
            "source": "form",
        },
    )
    return response.get_json()


# ── Submit lead tests ─────────────────────────────────────


def test_submit_lead_success(client, listing_id):
    response = client.post(
        f"/leads/{listing_id}",
        json={
            "visitor_name": "Khalid Hassan",
            "visitor_phone": "0551234567",
            "message": "Interested!",
            "source": "form",
        },
    )
    data = response.get_json()

    assert response.status_code == 201
    assert "lead_id" in data


def test_submit_lead_whatsapp_source(client, listing_id):
    response = client.post(
        f"/leads/{listing_id}",
        json={
            "visitor_name": "Sara",
            "visitor_phone": "0559999999",
            "source": "whatsapp",
        },
    )
    assert response.status_code == 201


def test_submit_lead_invalid_listing(client):
    response = client.post(
        "/leads/000000000000000000000000",
        json={"visitor_name": "Khalid", "visitor_phone": "0551234567"},
    )
    assert response.status_code == 404


def test_submit_lead_missing_fields(client, listing_id):
    response = client.post(
        f"/leads/{listing_id}",
        json={
            "visitor_name": "Khalid"
            # missing visitor_phone
        },
    )
    assert response.status_code == 400


# ── Broker inbox tests ────────────────────────────────────


def test_get_inbox(client, auth_headers, submitted_lead):
    response = client.get("/leads/inbox", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 1
    assert data["leads"][0]["visitor_name"] == "Khalid Hassan"


def test_get_inbox_filter_by_status(client, auth_headers, submitted_lead):
    response = client.get("/leads/inbox?status=new", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert all(l["status"] == "new" for l in data["leads"])


def test_get_inbox_no_auth(client):
    response = client.get("/leads/inbox")
    assert response.status_code == 401


# ── Update status tests ───────────────────────────────────


def test_update_lead_status(client, auth_headers, submitted_lead):
    lead_id = submitted_lead["lead_id"]
    response = client.put(
        f"/leads/{lead_id}/status", json={"status": "contacted"}, headers=auth_headers
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["lead"]["status"] == "contacted"


def test_update_lead_invalid_status(client, auth_headers, submitted_lead):
    lead_id = submitted_lead["lead_id"]
    response = client.put(
        f"/leads/{lead_id}/status",
        json={"status": "invalid_status"},
        headers=auth_headers,
    )
    assert response.status_code == 400


# ── Stats tests ───────────────────────────────────────────


def test_get_lead_stats(client, auth_headers, submitted_lead):
    response = client.get("/leads/stats", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["by_status"]["new"] == 1
    assert data["by_source"]["form"] == 1
