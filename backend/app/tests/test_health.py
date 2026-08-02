"""Tests for health check endpoints."""
import pytest


def test_root_endpoint(client):
    """GET / should return 200 with application name and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "Lenny Growth Assistant Backend"
    assert data["status"] == "running"
    assert "version" in data


def test_health_endpoint(client):
    """GET /health should return a HealthResponse with status field."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "version" in data
    assert "provider" in data


def test_rag_status_endpoint(client):
    """GET /rag-status should return RAG index stats (even if not loaded)."""
    response = client.get("/rag-status")
    assert response.status_code == 200
    data = response.json()
    assert "loaded" in data
    assert isinstance(data["loaded"], bool)
    assert "chunk_count" in data
    assert isinstance(data["chunk_count"], int)


def test_openapi_docs(client):
    """GET /docs should return 200 (OpenAPI docs available)."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_json(client):
    """GET /openapi.json should return a valid OpenAPI spec."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "Lenny Growth Assistant API"
    assert "paths" in spec
    # Verify key endpoints are in the spec
    paths = spec["paths"]
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/sessions/" in paths or any(
        p.startswith("/api/v1/sessions") for p in paths
    )
