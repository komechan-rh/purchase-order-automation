from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.settings import settings


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_amazon_purchase(monkeypatch) -> None:
    test_api_key = "test-api-key"
    monkeypatch.setattr(settings, "backend_api_key", test_api_key)
    monkeypatch.setattr(settings, "amazon_email", "user@example.com")
    monkeypatch.setattr(settings, "amazon_password", "secret")

    async def fake_run_purchase(
        item_name: str,
        quantity: int,
        note: str,
        product_url: str | None = None,
    ) -> None:
        return None

    monkeypatch.setattr(main_module.purchase_service, "run", fake_run_purchase)

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "https://www.amazon.co.jp/dp/B000TEST",
            "message": "補充",
        },
        headers={"X-API-Key": test_api_key},
    )

    assert response.status_code == 200
    assert response.json() == {
        "item_name": "テスト商品",
        "quantity": 2,
        "note": "補充",
        "source": "gas",
        "status": "PENDING",
        "product_url": "https://www.amazon.co.jp/dp/B000TEST",
    }


def test_create_amazon_purchase_missing_api_key(monkeypatch) -> None:
    """Test that missing API key returns 500 error."""
    monkeypatch.setattr(settings, "backend_api_key", "")
    monkeypatch.setattr(settings, "amazon_email", "user@example.com")
    monkeypatch.setattr(settings, "amazon_password", "secret")

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "https://www.amazon.co.jp/dp/B000TEST",
            "message": "補充",
        },
        headers={"X-API-Key": "any-key"},
    )

    assert response.status_code == 500
    assert "BACKEND_API_KEY is not set" in response.json()["detail"]


def test_create_amazon_purchase_invalid_api_key(monkeypatch) -> None:
    """Test that invalid API key returns 401 error."""
    test_api_key = "test-api-key"
    monkeypatch.setattr(settings, "backend_api_key", test_api_key)
    monkeypatch.setattr(settings, "amazon_email", "user@example.com")
    monkeypatch.setattr(settings, "amazon_password", "secret")

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "https://www.amazon.co.jp/dp/B000TEST",
            "message": "補充",
        },
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_create_amazon_purchase_missing_amazon_credentials(monkeypatch) -> None:
    """Test that missing Amazon credentials returns 500 error."""
    test_api_key = "test-api-key"
    monkeypatch.setattr(settings, "backend_api_key", test_api_key)
    monkeypatch.setattr(settings, "amazon_email", "")
    monkeypatch.setattr(settings, "amazon_password", "")

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "https://www.amazon.co.jp/dp/B000TEST",
            "message": "補充",
        },
        headers={"X-API-Key": test_api_key},
    )

    assert response.status_code == 500
    assert "Amazon credentials are not set" in response.json()["detail"]


def test_create_amazon_purchase_invalid_product_url(monkeypatch) -> None:
    """Test that invalid product URL returns 422 error."""
    test_api_key = "test-api-key"
    monkeypatch.setattr(settings, "backend_api_key", test_api_key)
    monkeypatch.setattr(settings, "amazon_email", "user@example.com")
    monkeypatch.setattr(settings, "amazon_password", "secret")

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "invalid-url",
            "message": "補充",
        },
        headers={"X-API-Key": test_api_key},
    )

    assert response.status_code == 422
    assert "Invalid product URL" in response.json()["detail"]


def test_create_amazon_purchase_non_amazon_url(monkeypatch) -> None:
    """Test that non-Amazon URL returns 422 error."""
    test_api_key = "test-api-key"
    monkeypatch.setattr(settings, "backend_api_key", test_api_key)
    monkeypatch.setattr(settings, "amazon_email", "user@example.com")
    monkeypatch.setattr(settings, "amazon_password", "secret")

    response = client.post(
        "/api/purchases/amazon",
        json={
            "name": "テスト商品",
            "count": 2,
            "product_url": "https://www.google.com",
            "message": "補充",
        },
        headers={"X-API-Key": test_api_key},
    )

    assert response.status_code == 422
    assert "Only Amazon product URLs are supported" in response.json()["detail"]
