import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

def test_research_endpoint_accepts_valid_query():
    # Use patch to prevent actual background task execution in DB
    with patch("src.services.research_service.ResearchService.create_job") as mock_create:
        mock_create.return_value = None
        response = client.post(
            "/api/v1/research",
            json={"query": "Valid research query for testing", "max_iterations": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
