# tests/test_listings.py
import pytest
from app import create_app
from app.auth.models import User
from app.brokers.models import BrokerProfile
from app.listings.models import Listing


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client
    Listing.objects.delete()
    BrokerProfile.objects.delete()
    User.objects.delete()


@pytest.fixture
def auth_headers(client):
    """Register, create profile, return auth headers."""
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
def sample_listing_data():
    return {
        "title": "Modern Apartment in Damascus",
        "description": "Spacious and bright apartment",
        "property_type": "apartment",
        "purpose": "sale",
        "price": 75000,
        "currency": "USD",
        "city": "Damascus",
        "district": "Mezzeh",
        "area_sqm": 120,
        "bedrooms": 3,
        "bathrooms": 2,
    }


@pytest.fixture
def created_listing(client, auth_headers, sample_listing_data):
    response = client.post("/listings/", json=sample_listing_data, headers=auth_headers)
    return response.get_json()


# ── Create tests ─────────────────────────────────────────


def test_create_listing_success(client, auth_headers, sample_listing_data):
    response = client.post("/listings/", json=sample_listing_data, headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 201
    assert data["listing"]["title"] == "Modern Apartment in Damascus"
    assert data["listing"]["city"] == "Damascus"
    assert data["listing"]["status"] == "active"


def test_create_listing_no_auth(client, sample_listing_data):
    response = client.post("/listings/", json=sample_listing_data)
    assert response.status_code == 401


def test_create_listing_invalid_data(client, auth_headers):
    response = client.post(
        "/listings/", json={"title": "X", "price": -100}, headers=auth_headers
    )
    assert response.status_code == 400


# ── Read tests ───────────────────────────────────────────


def test_get_listing(client, created_listing):
    listing_id = created_listing["listing"]["id"]
    response = client.get(f"/listings/{listing_id}")

    assert response.status_code == 200
    assert response.get_json()["title"] == "Modern Apartment in Damascus"


def test_get_listing_increments_views(client, created_listing):
    listing_id = created_listing["listing"]["id"]

    client.get(f"/listings/{listing_id}")
    client.get(f"/listings/{listing_id}")
    response = client.get(f"/listings/{listing_id}")

    assert response.get_json()["views_count"] == 3


def test_get_listing_invalid_id(client):
    response = client.get("/listings/notanid")
    assert response.status_code == 400


def test_browse_listings(client, created_listing):
    response = client.get("/listings/")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] >= 1


def test_browse_listings_filter_city(client, created_listing):
    response = client.get("/listings/?city=Damascus")
    data = response.get_json()

    assert response.status_code == 200
    assert all(l["city"] == "Damascus" for l in data["listings"])


def test_get_my_listings(client, auth_headers, created_listing):
    response = client.get("/listings/my", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["total"] == 1


# ── Update tests ─────────────────────────────────────────


def test_update_listing(client, auth_headers, created_listing):
    listing_id = created_listing["listing"]["id"]
    response = client.put(
        f"/listings/{listing_id}",
        json={"price": 80000, "status": "paused"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["listing"]["price"] == 80000
    assert data["listing"]["status"] == "paused"


def test_update_listing_unauthorized(client, created_listing):
    # register a second broker
    listing_id = created_listing["listing"]["id"]

    client.post(
        "/auth/register",
        json={
            "name": "Other Broker",
            "email": "other@test.com",
            "phone": "0509999999",
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login", json={"email": "other@test.com", "password": "password123"}
    )
    other_token = login.get_json()["access_token"]

    client.post(
        "/brokers/profile",
        json={"display_name": "Other Broker"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    response = client.put(
        f"/listings/{listing_id}",
        json={"price": 1},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


# ── Delete tests ─────────────────────────────────────────


def test_delete_listing(client, auth_headers, created_listing):
    listing_id = created_listing["listing"]["id"]
    response = client.delete(f"/listings/{listing_id}", headers=auth_headers)

    assert response.status_code == 200
    assert client.get(f"/listings/{listing_id}").status_code == 404
