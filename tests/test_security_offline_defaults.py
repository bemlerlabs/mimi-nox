from __future__ import annotations

import argparse
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_given_run_server_without_host_when_parser_used_then_binds_loopback_by_default():
    """
    GIVEN run_server.py is started without host flags
    WHEN arguments are parsed
    THEN the API binds to loopback instead of the whole LAN.
    """
    from run_server import build_parser

    parser = build_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"


def test_given_foreign_origin_when_cors_preflight_then_no_write_access_is_granted(tmp_path, monkeypatch):
    """
    GIVEN a random web page on the LAN
    WHEN it preflights a write endpoint
    THEN MiMi Nox does not grant CORS access.
    """
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))
    from server.main import create_app

    client = TestClient(create_app())
    response = client.options(
        "/api/memory/store",
        headers={
            "Origin": "http://evil.example.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None


def test_given_localhost_origin_when_cors_preflight_then_allowed(tmp_path, monkeypatch):
    """
    GIVEN the local PWA origin
    WHEN it preflights an API request
    THEN CORS still works for local development and desktop use.
    """
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))
    from server.main import create_app

    client = TestClient(create_app())
    response = client.options(
        "/api/memory/store",
        headers={
            "Origin": "http://127.0.0.1:8765",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:8765"


def test_given_mobile_qr_default_when_lan_is_reachable_then_lan_url_and_no_tunnel(tmp_path, monkeypatch):
    """
    GIVEN mobile pairing is requested without public mode
    WHEN LAN is reachable
    THEN auto mode keeps the QR LAN-only and does not start a public tunnel.
    """
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))
    from server.main import create_app

    with patch("server.routes.mobile.get_local_ip", return_value="192.168.1.50"), patch(
        "server.routes.mobile._lan_probe_succeeds", return_value=True
    ), patch("server.routes.mobile.tunnel_manager") as tunnel:
        tunnel.public_url = "https://example.localhost.run"
        client = TestClient(create_app())
        response = client.get("/api/mobile/qr")

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "http://192.168.1.50:8765/mobile.html"
    assert data["mode"] == "lan"
    assert data["is_public"] is False
    assert data["requires_internet"] is False
    tunnel.start_tunnel.assert_not_called()


def test_given_mobile_qr_public_mode_when_requested_then_tunnel_is_explicit(tmp_path, monkeypatch):
    """
    GIVEN public mobile pairing is explicitly requested
    WHEN a tunnel URL is available
    THEN the response is marked public and internet-dependent.
    """
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))
    from server.main import create_app

    with patch("server.routes.mobile.get_local_ip", return_value="192.168.1.50"), patch(
        "server.routes.mobile._lan_probe_succeeds", return_value=True
    ), patch("server.routes.mobile.tunnel_manager") as tunnel:
        tunnel.public_url = "https://example.localhost.run"
        client = TestClient(create_app())
        response = client.get("/api/mobile/qr?mode=public")

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.localhost.run/mobile.html"
    assert data["mode"] == "public"
    assert data["is_public"] is True
    assert data["requires_internet"] is True
    tunnel.start_tunnel.assert_called_once()


def test_given_mobile_qr_auto_when_lan_is_not_reachable_then_tunnel_restores_scan_flow(tmp_path, monkeypatch):
    """
    GIVEN mobile pairing is requested from a loopback-only desktop server
    WHEN a tunnel URL is available
    THEN auto mode remains LAN-first and does not create a public tunnel.
    """
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))
    monkeypatch.setenv("MIMI_NOX_HOST", "127.0.0.1")
    from server.main import create_app

    with patch("server.routes.mobile.get_local_ip", return_value="192.168.1.50"), patch(
        "server.routes.mobile.tunnel_manager"
    ) as tunnel:
        tunnel.public_url = "https://example.localhost.run"
        client = TestClient(create_app())
        response = client.get("/api/mobile/qr")

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "http://192.168.1.50:8765/mobile.html"
    assert data["mode"] == "lan"
    assert data["is_public"] is False
    assert data["requires_internet"] is False
    assert "miminox start --lan" in data["message"]
    tunnel.start_tunnel.assert_not_called()


def test_given_autonomous_request_when_sandbox_checked_then_auto_approval_is_never_allowed():
    """
    GIVEN a chat request sets autonomous=true
    WHEN sandbox auto-approval policy is checked
    THEN risky tools still require explicit approval.
    """
    from server.routes.chat import sandbox_auto_approval_allowed

    assert sandbox_auto_approval_allowed(autonomous=False) is False
    assert sandbox_auto_approval_allowed(autonomous=True) is False
