from __future__ import annotations

import contextlib
import base64
import json
import shutil
import subprocess
import threading
import time
from io import BytesIO
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright
import qrcode


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app" / "src"
OUT_DIR = ROOT / "docs" / "media"
FRAME_DIR = OUT_DIR / "frames"
LAN_MOBILE_URL = "http://192.168.1.23:8765/mobile.html"


SKILLS = [
    {"name": "Writer", "trigger": "/write", "description": "Schreibt E-Mails und Texte.", "tools": ["write"], "is_builtin": True},
    {"name": "Files", "trigger": "/files", "description": "Arbeitet mit lokalen Dateien.", "tools": ["files"], "is_builtin": True},
    {"name": "Review", "trigger": "/review", "description": "Prueft Code und Plaene.", "tools": ["review"], "is_builtin": True},
    {"name": "Research", "trigger": "/research", "description": "Optional online mit Quellen.", "tools": ["web"], "is_builtin": True},
    {"name": "Shell", "trigger": "/shell", "description": "Terminal-Hilfe mit Approval.", "tools": ["shell"], "is_builtin": True},
    {"name": "Scan", "trigger": "/scan", "description": "Analysiert Bilder und Screenshots.", "tools": ["vision"], "is_builtin": True},
]


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(
                {
                    "status": "ok",
                    "ollama": True,
                    "active_model": "gemma4:e4b",
                    "active_provider": "local_ollama",
                    "offline_capable": True,
                    "requires_internet": False,
                    "model_installed": True,
                }
            )
            return
        if parsed.path == "/api/model/providers":
            self._json(
                {
                    "active": {
                        "provider": "local_ollama",
                        "model": "gemma4:e4b",
                        "base_url": "http://localhost:11434",
                        "requires_internet": False,
                        "offline_capable": True,
                    },
                    "providers": [{"provider": "local_ollama", "model": "gemma4:e4b"}],
                    "local_models": ["gemma4:e4b"],
                }
            )
            return
        if parsed.path == "/api/skills":
            self._json({"skills": SKILLS})
            return
        if parsed.path == "/api/mobile/status":
            self._json({"connected": False})
            return
        if parsed.path == "/api/mobile/qr":
            self._json(
                {
                    "url": LAN_MOBILE_URL,
                    "qr_base64": qr_base64(LAN_MOBILE_URL),
                    "mode": "lan",
                    "is_public": False,
                    "requires_internet": False,
                    "lan_reachable": True,
                    "message": "",
                }
            )
            return
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat/stream":
            body = "\n".join(
                [
                    'data: {"type":"chunk","data":"MiMi Nox laeuft lokal mit gemma4:e4b. "}',
                    'data: {"type":"chunk","data":"Du kannst chatten, Bilder analysieren, Dateien pruefen und Skills starten."}',
                    'data: {"type":"done"}',
                    "",
                ]
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return self._json({"ok": True})


@contextlib.contextmanager
def static_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def capture(page, name: str) -> Path:
    path = FRAME_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def qr_base64(value: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=6)
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_gif(frames: list[Path], name: str, durations: list[int]) -> Path:
    images = [Image.open(frame).convert("RGB") for frame in frames]
    gif_path = OUT_DIR / f"{name}.gif"
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return gif_path


def build_mp4(frames: list[Path], name: str) -> Path | None:
    if not shutil.which("ffmpeg"):
        return None
    list_file = FRAME_DIR / "frames.txt"
    with list_file.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(f"file '{frame.name}'\n")
            handle.write("duration 1.1\n")
        handle.write(f"file '{frames[-1].name}'\n")
    mp4_path = OUT_DIR / f"{name}.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            "fps=12,format=yuv420p",
            str(mp4_path),
        ],
        cwd=FRAME_DIR,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return mp4_path


def capture_desktop_demo(browser, url: str) -> list[Path]:
    page = browser.new_page(viewport={"width": 1180, "height": 760}, device_scale_factor=1)
    page.add_init_script(
        """
        localStorage.setItem('mimi-nox-lang', 'de');
        localStorage.setItem('mimi_nox_onboarded', '1');
        """
    )
    page.goto(f"{url}?qa=readme-demo", wait_until="domcontentloaded")
    page.wait_for_function("() => window._nox")
    page.wait_for_timeout(500)
    frames = [capture(page, "desktop_01_home")]

    page.locator("#chat-input").fill("/write Schreibe eine kurze professionelle Terminverschiebung")
    frames.append(capture(page, "desktop_02_prompt"))

    page.locator("#send-btn").click()
    page.wait_for_function("() => document.body.innerText.includes('Du kannst chatten')")
    frames.append(capture(page, "desktop_03_answer"))

    page.locator("#btn-provider-settings").click()
    page.wait_for_selector("#provider-modal:not(.hidden)")
    frames.append(capture(page, "desktop_04_provider"))

    page.locator("#provider-cancel-btn").click()
    page.locator("#btn-mobile-pairing").click()
    page.wait_for_selector("#mobile-qr-overlay:not(.hidden)")
    frames.append(capture(page, "desktop_05_mobile_pairing"))

    page.locator("#mobile-qr-close-btn").click()
    page.locator("#tab-skills").click()
    page.wait_for_timeout(500)
    frames.append(capture(page, "desktop_06_skills"))

    page.close()
    return frames


def capture_mobile_demo(browser, url: str) -> list[Path]:
    mobile_url = url.replace("/index.html", "/mobile.html")
    page = browser.new_page(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
    )
    page.add_init_script("localStorage.setItem('mimi-nox-lang', 'de');")
    page.goto(f"{mobile_url}?qa=readme-mobile-demo", wait_until="domcontentloaded")
    page.wait_for_selector("#input")
    page.wait_for_timeout(500)
    frames = [capture(page, "mobile_01_home")]

    page.locator('#mobile-skill-chips .skill-chip[data-trigger="/write"]').click()
    frames.append(capture(page, "mobile_02_skill"))

    page.locator("#input").fill("/write Antworte kurz: MiMi Nox ist jetzt am Handy verbunden")
    frames.append(capture(page, "mobile_03_prompt"))

    page.locator("#send-btn").click()
    page.wait_for_function("() => document.body.innerText.includes('MiMi Nox laeuft lokal')")
    frames.append(capture(page, "mobile_04_answer"))

    page.locator('#mobile-skill-chips .skill-chip[data-trigger="/research"]').click()
    page.locator("#input").fill("/research aktuelle lokale KI news")
    page.locator("#send-btn").click()
    page.wait_for_selector("#online-confirm:not(.hidden)")
    frames.append(capture(page, "mobile_05_online_optin"))

    page.close()
    return frames


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for old in FRAME_DIR.glob("*.png"):
        old.unlink()

    with static_server() as url, sync_playwright() as p:
        browser = p.chromium.launch()
        desktop_frames = capture_desktop_demo(browser, url)
        mobile_frames = capture_mobile_demo(browser, url)
        browser.close()

    gif = build_gif(desktop_frames, "mimi-nox-demo", [1000, 900, 1200, 1200, 1200, 1400])
    mp4 = build_mp4(desktop_frames, "mimi-nox-demo")
    mobile_gif = build_gif(mobile_frames, "mimi-nox-mobile-qr-demo", [1100, 1000, 1000, 1500, 1500])
    mobile_mp4 = build_mp4(mobile_frames, "mimi-nox-mobile-qr-demo")
    print(f"GIF: {gif.relative_to(ROOT)}")
    if mp4:
        print(f"MP4: {mp4.relative_to(ROOT)}")
    print(f"Mobile GIF: {mobile_gif.relative_to(ROOT)}")
    if mobile_mp4:
        print(f"Mobile MP4: {mobile_mp4.relative_to(ROOT)}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"Done in {time.time() - start:.1f}s")
