import pytest
from fastapi.testclient import TestClient
from server.main import create_app
from unittest.mock import patch

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_mobile_qr_offline_fallback(client):
    """Given air-gapped status, when GET /api/mobile/qr is requested, then it should use local IP."""
    with patch("server.routes.mobile.is_internet_available", return_value=False), \
         patch("server.routes.mobile.get_local_ip", return_value="192.168.1.50"), \
         patch("server.routes.mobile.tunnel_manager") as mock_tunnel:
        
        response = client.get("/api/mobile/qr")
        assert response.status_code == 200
        data = response.json()
        
        # Then: URL should be local, not from tunnel
        assert data["url"] == "http://192.168.1.50:8765/mobile.html"
        # And: Tunnel should NOT have been started
        mock_tunnel.start_tunnel.assert_not_called()

def test_mobile_qr_online_flow(client):
    """Given internet available, when GET /api/mobile/qr is requested, then it should try tunnel."""
    with patch("server.routes.mobile.is_internet_available", return_value=True), \
         patch("server.routes.mobile.get_local_ip", return_value="192.168.1.50"), \
         patch("server.routes.mobile.tunnel_manager") as mock_tunnel:
        
        mock_tunnel.public_url = "https://miminox.serveo.net"
        mock_tunnel.start_tunnel.return_value = None
        
        response = client.get("/api/mobile/qr")
        assert response.status_code == 200
        data = response.json()
        
        # Then: URL should be from tunnel
        assert data["url"] == "https://miminox.serveo.net/mobile.html"
        # And: Tunnel SHOULD have been started
        mock_tunnel.start_tunnel.assert_called_once()
