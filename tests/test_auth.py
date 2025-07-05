"""
Test authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient, test_user):
    """Test user registration."""
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert data["tier"] == "free"


def test_login_user(client: TestClient, test_user):
    """Test user login."""
    # First register the user
    client.post("/api/v1/auth/register", json=test_user)
    
    # Then login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["tier"] == "free"


def test_get_current_user(client: TestClient, test_user):
    """Test getting current user info."""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user)
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    
    token = login_response.json()["access_token"]
    
    # Get user info
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]


def test_duplicate_registration(client: TestClient, test_user):
    """Test duplicate user registration."""
    # Register user
    client.post("/api/v1/auth/register", json=test_user)
    
    # Try to register again
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_invalid_login(client: TestClient, test_user):
    """Test invalid login."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_create_api_key(client: TestClient, test_user):
    """Test API key creation."""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user)
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    
    token = login_response.json()["access_token"]
    
    # Create API key
    response = client.post(
        "/api/v1/auth/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("kalpi_")


def test_list_api_keys(client: TestClient, test_user):
    """Test listing API keys."""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user)
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    
    token = login_response.json()["access_token"]
    
    # Create API key
    client.post(
        "/api/v1/auth/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # List API keys
    response = client.get(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "api_keys" in data
    assert len(data["api_keys"]) == 1
    assert data["api_keys"][0]["key_hint"].startswith("kalpi_")
