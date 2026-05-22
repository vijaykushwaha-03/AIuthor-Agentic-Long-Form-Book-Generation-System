"""
AIuthor Backend Tests — Health & Version Endpoint Tests.

Tests:
  1. test_health_returns_200
  2. test_health_response_schema
  3. test_health_status_is_ok
  4. test_health_env_is_test
  5. test_version_returns_200
  6. test_version_response_schema
  7. test_version_service_name
  8. test_unknown_route_returns_404
  9. test_config_version_matches_version_endpoint
 10. test_cors_header_present_on_health
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# /health endpoint tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests for GET /health"""

    def test_health_returns_200(self, client: TestClient):
        """Health check must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. Body: {response.text}"
        )

    def test_health_response_schema(self, client: TestClient):
        """Response must contain 'status', 'env', and 'version' keys."""
        response = client.get("/health")
        body = response.json()
        assert "status" in body, "Missing 'status' key in /health response"
        assert "env" in body, "Missing 'env' key in /health response"
        assert "version" in body, "Missing 'version' key in /health response"

    def test_health_status_is_ok(self, client: TestClient):
        """The 'status' field must equal 'ok'."""
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_env_is_test(self, client: TestClient):
        """The 'env' field must equal 'test' (set in conftest)."""
        response = client.get("/health")
        assert response.json()["env"] == "test"

    def test_health_version_is_string(self, client: TestClient):
        """The 'version' field must be a non-empty string."""
        response = client.get("/health")
        version = response.json()["version"]
        assert isinstance(version, str) and len(version) > 0

    def test_health_content_type_is_json(self, client: TestClient):
        """Response content-type must be application/json."""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")


# ─────────────────────────────────────────────────────────────────────────────
# /api/version endpoint tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVersionEndpoint:
    """Tests for GET /api/version"""

    def test_version_returns_200(self, client: TestClient):
        """Version endpoint must return HTTP 200."""
        response = client.get("/api/version")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. Body: {response.text}"
        )

    def test_version_response_schema(self, client: TestClient):
        """Response must contain 'version' and 'service' keys."""
        response = client.get("/api/version")
        body = response.json()
        assert "version" in body, "Missing 'version' key in /api/version response"
        assert "service" in body, "Missing 'service' key in /api/version response"

    def test_version_service_name(self, client: TestClient):
        """The 'service' field must be 'aiuthor-backend'."""
        response = client.get("/api/version")
        assert response.json()["service"] == "aiuthor-backend"

    def test_version_value_matches_health(self, client: TestClient):
        """The version in /api/version must match the version in /health."""
        health_version = client.get("/health").json()["version"]
        api_version = client.get("/api/version").json()["version"]
        assert health_version == api_version, (
            f"/health version '{health_version}' != /api/version version '{api_version}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Config & error handling tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigAndErrors:
    """Tests for config loading and error handling."""

    def test_config_version_matches_version_endpoint(self, client: TestClient):
        """
        Settings.APP_VERSION must match the value returned by /api/version.
        This ensures no code path changes the version string after Settings loads.
        """
        from app.config import get_settings
        settings = get_settings()
        response = client.get("/api/version")
        assert response.json()["version"] == settings.APP_VERSION

    def test_unknown_route_returns_404(self, client: TestClient):
        """Requests to non-existent routes must return 404."""
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404

    def test_cors_header_present_on_health(self, client: TestClient):
        """
        A preflight-like request with Origin header must include
        Access-Control-Allow-Origin in the response.

        Note: TestClient follows CORS middleware — we send a real Origin header.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        # CORS header should be present when origin is in the allowed list
        assert "access-control-allow-origin" in response.headers, (
            "CORS header 'access-control-allow-origin' missing. "
            "Check ALLOWED_ORIGINS config."
        )

    def test_config_app_env_is_test(self):
        """Settings.APP_ENV must be 'test' in the test environment."""
        from app.config import get_settings
        settings = get_settings()
        assert settings.APP_ENV == "test"

    def test_config_log_level_is_valid(self):
        """Settings.LOG_LEVEL must be one of the valid Python logging levels."""
        from app.config import get_settings
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        settings = get_settings()
        assert settings.LOG_LEVEL in valid_levels
