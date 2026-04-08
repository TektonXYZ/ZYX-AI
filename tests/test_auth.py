"""
Tests for authentication endpoints.
"""

import pytest


def test_root_endpoint(client):
    """Test root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_register_endpoint(self, client):
        """Test user registration."""
        response = client.post(
            "/auth/register",
            params={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 201
        assert "message" in response.json()
    
    def test_login_endpoint(self, client):
        """Test user login."""
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
