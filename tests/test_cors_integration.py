import pytest
from fastapi.testclient import TestClient
from server.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_cors_blocks_unpaired_lan_origins(client):
    # Simulate a request from a random LAN page trying to reach the local API.
    headers = {
        "Origin": "http://192.168.178.50:8765",
        "Access-Control-Request-Method": "GET",
    }
    
    # Pre-flight OPTIONS request
    response = client.options("/api/mobile/qr", headers=headers)
    assert response.status_code in (200, 400)
    
    # The local app is served same-origin; unrelated LAN origins must not be granted CORS.
    cors_allow_origin = response.headers.get("access-control-allow-origin")
    assert cors_allow_origin is None
