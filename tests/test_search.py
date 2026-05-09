# tests/test_search.py
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
def seeded_data(client):
    """
    Create two brokers with multiple listings across cities and types.
    This gives us meaningful data to search and filter against.
    """
    # broker 1 — Damascus
    client.post(
        "/auth/register",
        json={
            "name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "phone": "0501111111",
            "password": "password123",
        },
    )
    r = client.post(
        "/auth/login", json={"email": "ahmed@test.com", "password": "password123"}
    )
    token1 = r.get_json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    client.post(
        "/brokers/profile",
        json={"display_name": "Ahmed Damascus", "city": "Damascus"},
        headers=headers1,
    )

    # broker 2 — Aleppo
    client.post(
        "/auth/register",
        json={
            "name": "Sara Hassan",
            "email": "sara@test.com",
            "phone": "0502222222",
            "password": "password123",
        },
    )
    r = client.post(
        "/auth/login", json={"email": "sara@test.com", "password": "password123"}
    )
    token2 = r.get_json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    client.post(
        "/brokers/profile",
        json={"display_name": "Sara Aleppo", "city": "Aleppo"},
        headers=headers2,
    )

    # listings for broker 1
    client.post(
        "/listings/",
        headers=headers1,
        json={
            "title": "Modern Apartment in Mezzeh",
            "property_type": "apartment",
            "purpose": "sale",
            "price": 75000,
            "city": "Damascus",
            "district": "Mezzeh",
            "bedrooms": 3,
            "furnished": True,
        },
    )
    client.post(
        "/listings/",
        headers=headers1,
        json={
            "title": "Villa for Rent in Damascus",
            "property_type": "villa",
            "purpose": "rent",
            "price": 2000,
            "city": "Damascus",
            "bedrooms": 5,
        },
    )

    # listings for broker 2
    client.post(
        "/listings/",
        headers=headers2,
        json={
            "title": "Office Space in Aleppo",
            "property_type": "office",
            "purpose": "rent",
            "price": 800,
            "city": "Aleppo",
        },
    )
    client.post(
        "/listings/",
        headers=headers2,
        json={
            "title": "Land for Sale in Aleppo",
            "property_type": "land",
            "purpose": "sale",
            "price": 120000,
            "city": "Aleppo",
        },
    )

    return {"headers1": headers1, "headers2": headers2}


# ── Filter search tests ───────────────────────────────────


def test_search_no_filters(client, seeded_data):
    response = client.get("/search/")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 4


def test_search_filter_by_city(client, seeded_data):
    response = client.get("/search/?city=Damascus")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 2
    assert all(l["city"] == "Damascus" for l in data["results"])


def test_search_filter_by_purpose(client, seeded_data):
    response = client.get("/search/?purpose=sale")
    data = response.get_json()

    assert response.status_code == 200
    assert all(l["purpose"] == "sale" for l in data["results"])


def test_search_filter_by_type(client, seeded_data):
    response = client.get("/search/?property_type=apartment")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 1


def test_search_filter_price_range(client, seeded_data):
    response = client.get("/search/?min_price=1000&max_price=80000")
    data = response.get_json()

    assert response.status_code == 200
    assert all(1000 <= l["price"] <= 80000 for l in data["results"])


def test_search_filter_furnished(client, seeded_data):
    response = client.get("/search/?furnished=true")
    data = response.get_json()

    assert response.status_code == 200
    assert all(l["furnished"] for l in data["results"])


def test_search_sort_price_asc(client, seeded_data):
    response = client.get("/search/?sort=price_asc")
    data = response.get_json()
    prices = [l["price"] for l in data["results"]]

    assert response.status_code == 200
    assert prices == sorted(prices)


def test_search_sort_price_desc(client, seeded_data):
    response = client.get("/search/?sort=price_desc")
    data = response.get_json()
    prices = [l["price"] for l in data["results"]]

    assert response.status_code == 200
    assert prices == sorted(prices, reverse=True)


def test_search_pagination(client, seeded_data):
    response = client.get("/search/?per_page=2&page=1")
    data = response.get_json()

    assert response.status_code == 200
    assert len(data["results"]) == 2
    assert data["pagination"]["pages"] == 2


# ── Discovery tests ───────────────────────────────────────


def test_get_cities(client, seeded_data):
    response = client.get("/search/cities")
    data = response.get_json()

    assert response.status_code == 200
    city_names = [c["city"] for c in data["cities"]]
    assert "Damascus" in city_names
    assert "Aleppo" in city_names


def test_get_categories(client, seeded_data):
    response = client.get("/search/categories")
    data = response.get_json()

    assert response.status_code == 200
    assert "apartment" in data["categories"]
    assert "villa" in data["categories"]


def test_discover_brokers(client, seeded_data):
    response = client.get("/search/brokers")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 2


def test_discover_brokers_filter_city(client, seeded_data):
    response = client.get("/search/brokers?city=Aleppo")
    data = response.get_json()

    assert response.status_code == 200
    assert data["pagination"]["total"] == 1
    assert data["brokers"][0]["city"] == "Aleppo"
