# This file contains automated tests for the FastAPI backend.
# The tests use pytest and FastAPI's TestClient to simulate API requests.

import sys
import os

# Add the parent directory (backend) to the python path
# This allows the test file to import the main application
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app  # Import your main FastAPI application instance

# Create a TestClient instance to make requests to your app.
# The base_url is set to http://test.local to avoid making real requests.
client = TestClient(app)

# =============================================================================
# Test API Endpoints
# =============================================================================

# Test the root endpoint to ensure the server is running.
def test_read_main():
    """
    Test the root endpoint for a simple health check.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the SkillShare Platform API!"}


# Test the user signup process with a valid user.
def test_create_user_valid():
    """
    Test the POST /users/ endpoint with valid user data.
    """
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Password1!"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    # Check that the response contains the expected fields and doesn't expose the password hash.
    assert "id" in response.json()
    assert response.json()["username"] == "testuser"
    assert "password" not in response.json()


# Test the user signup process with an invalid password.
def test_create_user_invalid_password():
    """
    Test the POST /users/ endpoint with an invalid password that
    fails the custom password_complexity validator.
    """
    user_data = {
        "username": "invaliduser",
        "email": "invalid@example.com",
        "password": "short"  # Invalid password (too short)
    }
    response = client.post("/users/", json=user_data)
    # A 422 status code indicates a validation error.
    assert response.status_code == 422


# Test the login process and retrieve a JWT token.
def test_login_user():
    """
    Test the POST /users/login endpoint to ensure a valid token is returned.
    This also implicitly tests the verify_password function.
    """
    # First, create a user to log in with.
    client.post("/users/", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "Password1!"
    })
    
    # Now, attempt to log in with the new user's credentials.
    login_data = {
        "username": "login@example.com",
        "password": "Password1!"
    }
    response = client.post("/users/login", data=login_data)
    assert response.status_code == 200
    # Check that the response contains an access token and token type.
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


# Test a protected endpoint with and without a valid token.
def test_get_current_user_protected():
    """
    Test a protected endpoint to verify it requires authentication.
    """
    # First, log in a user to get a valid token.
    login_data = {
        "username": "login@example.com",
        "password": "Password1!"
    }
    login_response = client.post("/users/login", data=login_data)
    token = login_response.json()["access_token"]
    
    # Test the protected endpoint with the valid token in the header.
    headers = {"Authorization": f"Bearer {token}"}
    protected_response = client.get("/users/me", headers=headers)
    assert protected_response.status_code == 200
    assert "username" in protected_response.json()
    
    # Test the same endpoint without a token to ensure it fails.
    unauthorized_response = client.get("/users/me")
    assert unauthorized_response.status_code == 401
    assert unauthorized_response.json()["detail"] == "Not authenticated"
