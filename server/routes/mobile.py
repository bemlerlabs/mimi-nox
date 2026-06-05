"""server/routes/mobile.py – GET /api/mobile/qr"""

import io
import base64
import time
import os
import urllib.request
from urllib.parse import urlparse
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Literal

from utils.network import get_local_ip
from utils.tunnel import tunnel_manager

router = APIRouter(tags=["Mobile"])

# Global state for connection tracking
_device_connected = False

class MobileQRResponse(BaseModel):
    url: str
    qr_base64: str
    mode: str = "auto"
    is_public: bool = False
    requires_internet: bool = False
    lan_reachable: bool = True
    message: str = ""


def _is_loopback_host(host: str | None) -> bool:
    normalized = (host or "").strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _server_allows_lan(request: Request) -> bool:
    bound_host = os.environ.get("MIMI_NOX_HOST") or request.url.hostname
    return not _is_loopback_host(bound_host)


def _is_docker_runtime() -> bool:
    return os.environ.get("MIMI_NOX_DOCKER") == "1" or os.path.exists("/.dockerenv")


def _configured_mobile_base_url(port: int) -> str | None:
    host = (os.environ.get("MIMI_NOX_MOBILE_HOST") or "").strip()
    if not host:
        return None
    if "://" in host:
        parsed = urlparse(host)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return f"http://{host}:{port}".rstrip("/")


def _lan_probe_succeeds(base_url: str) -> bool:
    if os.environ.get("MIMI_NOX_SKIP_LAN_PROBE") == "1":
        return True
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=0.75) as response:
            return 200 <= response.status < 500
    except Exception:
        return False

def _start_public_tunnel(port: int) -> str | None:
    tunnel_manager.start_tunnel(port)
    first_seen_at = None
    for _ in range(140):
        if tunnel_manager.public_url and first_seen_at is None:
            first_seen_at = time.time()
        if first_seen_at is not None and time.time() - first_seen_at >= 2.0:
            break
        time.sleep(0.1)
    return tunnel_manager.public_url


@router.get("/mobile/qr", response_model=MobileQRResponse)
def get_mobile_qr(request: Request, mode: Literal["auto", "lan", "public"] = "auto") -> MobileQRResponse:
    """Returns the local or public URL and a base64 encoded QR code for mobile pairing."""
    global _device_connected
    _device_connected = False  # Reset on new pairing request
    port = request.url.port or 8765
    
    target_url = None
    is_public = False
    lan_reachable = _server_allows_lan(request)
    message = ""
    
    if mode == "public":
        target_url = _start_public_tunnel(port)
        is_public = bool(target_url)
    
    if not target_url:
        configured_mobile_base_url = _configured_mobile_base_url(port)
        docker_without_mobile_host = _is_docker_runtime() and configured_mobile_base_url is None
        ip = get_local_ip()
        target_url = configured_mobile_base_url or f"http://{ip}:{port}"
        if docker_without_mobile_host:
            lan_reachable = False
        if not lan_reachable:
            mode = "lan"
            if docker_without_mobile_host:
                message = (
                    "Docker cannot expose its internal network address to your phone. "
                    "Set MIMI_NOX_MOBILE_HOST to your Mac Wi-Fi IP or choose public QR mode explicitly."
                )
            else:
                message = (
                    "Mobile LAN pairing needs MiMi Nox started with LAN access. "
                    "Run: miminox start --lan"
                )
        elif not _lan_probe_succeeds(target_url):
            lan_reachable = False
            mode = "lan"
            message = (
                "MiMi Nox is in LAN mode, but this Mac is not answering on the Wi-Fi address. "
                "Allow Python/Terminal in macOS Firewall or Local Network permissions, then reopen the QR. "
                "Public QR is available only when you choose public mode explicitly."
            )
        else:
            mode = "lan"
    else:
        lan_reachable = True
    
    # Mobile users get the clean chat-only page
    mobile_url = f"{target_url}/mobile.html"
    
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(mobile_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return MobileQRResponse(
        url=mobile_url,
        qr_base64=qr_base64,
        mode=mode,
        is_public=is_public,
        requires_internet=is_public,
        lan_reachable=lan_reachable,
        message=message,
    )


@router.post("/mobile/ping")
def mobile_ping():
    """Triggered by the PWA when it opens on a smartphone."""
    global _device_connected
    _device_connected = True
    return {"status": "ok"}


@router.get("/mobile/status")
def mobile_status():
    """Polled by the Desktop UI while the QR code is open."""
    global _device_connected
    return {"connected": _device_connected}
