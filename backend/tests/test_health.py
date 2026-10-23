from fastapi.testclient import TestClient

from app.api.routes import health as health_routes
from app.db.session import DatabaseConfigurationError
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_ready_when_database_is_available(
    monkeypatch,
) -> None:
    monkeypatch.setattr(health_routes, "check_database_connection", lambda: None)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_endpoint_returns_unavailable_when_database_is_not_configured(
    monkeypatch,
) -> None:
    def raise_not_configured() -> None:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")

    monkeypatch.setattr(
        health_routes,
        "check_database_connection",
        raise_not_configured,
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "The service is not ready.",
        }
    }
