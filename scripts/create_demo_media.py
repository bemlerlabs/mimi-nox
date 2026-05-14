#!/usr/bin/env python3
"""
MiMi Nox — Professional Demo Video Generator (v3)
Produces real screen-recording MP4s via Playwright record_video.

Desktop video: 1280x720 continuous recording with smooth mouse/typing
Mobile video:  720x1280 continuous recording with mobile viewport

Requires: ffmpeg, playwright, pillow, qrcode
Usage:   python scripts/create_demo_media.py
"""

from __future__ import annotations

import base64
import contextlib
import json
import subprocess
import tempfile
import threading
import time
from io import BytesIO
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import qrcode

# ── Paths ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app" / "src"
OUT_DIR = ROOT / "docs" / "media"
TEMP_DIR = OUT_DIR / "temp"

LAN_MOBILE_URL = "http://192.168.1.23:8765/mobile.html"

# Video specs
DESKTOP_W, DESKTOP_H = 1280, 720
MOBILE_V_W, MOBILE_V_H = 720, 1280  # Upscaled mobile for README video
MOBILE_VIEWPORT_W, MOBILE_VIEWPORT_H = 390, 844  # iPhone 14

# Colors (Schwarzwald Edition)
GREEN = (34, 197, 94)
GREEN_LIGHT = (74, 222, 128)
BG_COLOR = (2, 5, 4)
WHITE = (240, 253, 244)
DIM = (107, 114, 128)

# ── Skills fixture ─────────────────────────────────────────────────────────

SKILLS = [
    {"name": "Writer", "trigger": "/write", "description": "Schreibt E-Mails und Texte.", "tools": ["write"], "is_builtin": True},
    {"name": "Files", "trigger": "/files", "description": "Arbeitet mit lokalen Dateien.", "tools": ["files"], "is_builtin": True},
    {"name": "Review", "trigger": "/review", "description": "Prueft Code und Plaene.", "tools": ["review"], "is_builtin": True},
    {"name": "Research", "trigger": "/research", "description": "Optional online mit Quellen.", "tools": ["web"], "is_builtin": True},
    {"name": "Shell", "trigger": "/shell", "description": "Terminal-Hilfe mit Approval.", "tools": ["shell"], "is_builtin": True},
    {"name": "Scan", "trigger": "/scan", "description": "Analysiert Bilder und Screenshots.", "tools": ["vision"], "is_builtin": True},
]

# ── Demo HTTP Server (fixture) ────────────────────────────────────────────

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
            self._json({
                "status": "ok", "ollama": True, "active_model": "gemma4:e4b",
                "active_provider": "local_ollama", "offline_capable": True,
                "requires_internet": False, "model_installed": True,
            })
            return
        if parsed.path == "/api/model/providers":
            self._json({
                "active": {"provider": "local_ollama", "model": "gemma4:e4b",
                           "base_url": "http://localhost:11434",
                           "requires_internet": False, "offline_capable": True},
                "providers": [{"provider": "local_ollama", "model": "gemma4:e4b"}],
                "local_models": ["gemma4:e4b"],
            })
            return
        if parsed.path == "/api/skills":
            self._json({"skills": SKILLS})
            return
        if parsed.path == "/api/mobile/status":
            self._json({"connected": False})
            return
        if parsed.path == "/api/mobile/qr":
            self._json({
                "url": LAN_MOBILE_URL, "qr_base64": qr_base64(LAN_MOBILE_URL),
                "mode": "lan", "is_public": False, "requires_internet": False,
                "lan_reachable": True, "message": "",
            })
            return
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat/stream":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                req = json.loads(raw_body)
                message = req.get("message", "")
            except Exception:
                message = ""

            # Return context-appropriate responses based on the prompt
            if "Terminverschiebung" in message or "termin" in message.lower():
                chunks = [
                    "/write Skill aktiviert — E-Mail verfassen.\n\n",
                    "Betreff: Terminverschiebung – Unser Gespräch am 18. Mai\n\n",
                    "Sehr geehrte Frau Müller,\n\n",
                    "leider muss ich unseren ursprünglich für Donnerstag, den 18. Mai um 14:00 Uhr vorgesehenen Termin verschieben. Wären Sie bereit, den Termin auf Freitag, den 19. Mai um 10:00 Uhr zu verlegen?\n\n",
                    "Ich bitte um Entschuldigung für die Unannehmlichkeiten und freue mich auf Ihre Bestätigung.\n\n",
                    "Mit freundlichen Grüßen\n",
                    "Ihr Team\n",
                ]
            elif "Handy" in message or "handy" in message.lower() or "mobil" in message.lower():
                chunks = [
                    "Ja, MiMi Nox ist jetzt über das Handy verbunden! 📱\n\n",
                    "Du kannst jetzt von überall auf deine lokalen AI-Funktionen zugreifen – vollständig offline über dein WLAN-Netzwerk. "
                    "Alle Skills wie /write, /files und /scan funktionieren auch auf dem Mobilgerät."
                ]
            else:
                chunks = [
                    "MiMi Nox läuft lokal mit gemma4:e4b. "
                    "Du kannst chatten, Bilder analysieren, Dateien prüfen und Skills starten."
                ]

            events = [{"type": "chunk", "data": c} for c in chunks] + [{"type": "done"}]
            body = "\n".join(
                [f"data: {json.dumps(event, ensure_ascii=False)}" for event in events] + [""]
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return self._json({"ok": True})

    def log_message(self, format, *args) -> None:
        # Suppress HTTP request logs during demo recording
        pass


@contextlib.contextmanager
def static_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ── QR Code helper ────────────────────────────────────────────────────────

def qr_base64(value: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=6)
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ── Font helper ───────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    if bold:
        candidates.extend([
            "/System/Library/Fonts/Helvetica Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ])
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ── Title / End card rendering ────────────────────────────────────────────

def make_title_card(text: str, sub: str, icon: str = "◑",
                    width: int = DESKTOP_W, height: int = DESKTOP_H) -> Path:
    bg = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(bg)
    y_center = height // 2
    draw.text((width // 2, y_center - 60), icon, fill=GREEN, anchor="mm", font=_font(100))
    draw.text((width // 2, y_center + 40), text, fill=WHITE, anchor="mm", font=_font(48, bold=True))
    draw.text((width // 2, y_center + 110), sub, fill=DIM, anchor="mm", font=_font(26))
    path = TEMP_DIR / "title_card.png"
    bg.save(path)
    return path


def make_end_card(text: str, width: int = DESKTOP_W, height: int = DESKTOP_H) -> Path:
    bg = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(bg)
    y_center = height // 2
    draw.text((width // 2, y_center - 30), text, fill=WHITE, anchor="mm", font=_font(40, bold=True))
    draw.text((width // 2, y_center + 40), "github.com/MimiTechAi/mimi-nox", fill=GREEN_LIGHT, anchor="mm", font=_font(24))
    path = TEMP_DIR / "end_card.png"
    bg.save(path)
    return path


def make_mobile_qr_intro() -> Path:
    """Create a professional mobile QR intro frame."""
    w, h = MOBILE_V_W, MOBILE_V_H
    bg = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(bg)

    title_font = _font(36, bold=True)
    body_font = _font(22)
    small_font = _font(17)

    draw.text((30, 80), "MiMi Nox", fill=WHITE, font=title_font)
    draw.ellipse((30, 126, 52, 148), fill=GREEN)
    draw.text((60, 122), "Lokal verbunden", fill=GREEN_LIGHT, font=body_font)

    draw.text((30, 220), "QR am Desktop scannen", fill=WHITE, font=_font(26, bold=True))
    draw.text((30, 260), "Dein Handy öffnet die mobile PWA im selben WLAN.", fill=DIM, font=small_font)

    qr_png = Image.open(BytesIO(base64.b64decode(qr_base64(LAN_MOBILE_URL)))).convert("RGB")
    qr_png = qr_png.resize((300, 300), Image.Resampling.NEAREST)
    qr_box = Image.new("RGB", (340, 340), "#f7fff9")
    qr_box.paste(qr_png, (20, 20))
    bg.paste(qr_box, (25, 340))

    draw.rounded_rectangle((30, 700, 360, 800), radius=20, outline="#14532d", width=2, fill="#03140a")
    draw.text((50, 725), "Standard: lokales Netzwerk", fill=GREEN, font=body_font)
    draw.text((50, 765), "Public Zugriff bleibt optional.", fill=DIM, font=small_font)

    path = TEMP_DIR / "mobile_qr_intro.png"
    bg.save(path)
    return path


# ── Human-like interaction helpers ────────────────────────────────────────

def human_click(page, selector: str, move_steps: int = 15, pause_after: float = 0.3) -> None:
    """Smoothly move mouse to element center, click, then pause."""
    el = page.locator(selector)
    page.wait_for_timeout(300)
    box = el.bounding_box()
    if box is None:
        el.click()
        if pause_after > 0:
            page.wait_for_timeout(int(pause_after * 1000))
        return
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    page.mouse.move(cx, cy, steps=move_steps)
    page.mouse.click(cx, cy)
    if pause_after > 0:
        page.wait_for_timeout(int(pause_after * 1000))


def human_type(page, selector: str, text: str, delay: int = 45) -> None:
    """Focus element, clear it, then type character-by-character with natural delay."""
    el = page.locator(selector)
    page.wait_for_timeout(300)
    el.click()
    page.wait_for_timeout(150)
    page.keyboard.press("Meta+a")
    page.keyboard.press("Backspace")
    page.wait_for_timeout(100)
    page.keyboard.type(text, delay=delay)
    page.wait_for_timeout(200)


def human_scroll(page, delta_y: int = -400, steps: int = 25) -> None:
    """Smooth scrolling via small wheel increments."""
    per_step = delta_y // steps
    for _ in range(steps):
        page.mouse.wheel(0, per_step)
    page.wait_for_timeout(400)


# ── FFmpeg helpers ─────────────────────────────────────────────────────────

def run_ffmpeg(cmd: list[str]) -> bool:
    """Execute ffmpeg. Returns True on success."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            err = result.stderr[-600:] if result.stderr else "no stderr"
            print(f"  [ERROR] ffmpeg exited {result.returncode}: {err[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  [ERROR] ffmpeg timed out (>120s)")
        return False
    except Exception as e:
        print(f"  [ERROR] ffmpeg: {e}")
        return False


def _probe_video(path: Path) -> tuple[int, int, float]:
    """Return (width, height, duration) for any video/image via ffprobe."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, timeout=10
    )
    data = json.loads(probe.stdout)
    vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    w = int(vs.get("width", 0))
    h = int(vs.get("height", 0))
    dur = float(data.get("format", {}).get("duration", "0"))
    return w, h, dur


def _img_to_mp4(src_png: Path, dst_mp4: Path, duration: float,
                out_w: int, out_h: int, fade: str | None = None) -> bool:
    """Encode a still image to an H.264 mp4 segment of given duration.

    Optionally adds a fadein/fadeout video filter for smooth transitions.
    """
    vf_parts = [f"scale={out_w}:{out_h}:flags=lanczos"]
    if fade == "in":
        vf_parts.append("fade=t=in:st=0:d=0.5")
    elif fade == "out":
        vf_parts.append(f"fade=t=out:st={duration - 0.5}:d=0.5")
    elif fade == "both":
        vf_parts.append("fade=t=in:st=0:d=0.5")
        vf_parts.append(f"fade=t=out:st={duration - 0.5}:d=0.5")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-framerate", "30",
        "-i", str(src_png),
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-an",
        str(dst_mp4),
    ]
    return run_ffmpeg(cmd)


def compose_video_mp4(title_png: Path, webm_path: Path, end_png: Path,
                      output_mp4: Path,
                      title_dur: float = 3.0, end_dur: float = 2.0) -> None:
    """Compose: [title card] + [screen recording] + [end card].

    Strategy: encode each piece to matching H.264 mp4, then concat with
    the concat demuxer (requires identical codec/resolution/fps).
    """
    out_w, out_h, webm_dur = _probe_video(webm_path)
    if webm_dur < 1:
        print(f"  [WARN] webm duration {webm_dur}s seems too short")

    # Step 1: Convert webm to h.264 mp4 (same resolution)
    video_mp4 = TEMP_DIR / "recording.mp4"
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(webm_path),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        str(video_mp4),
    ])

    # Step 2: Encode title and end cards as matching mp4s with fades
    title_mp4 = TEMP_DIR / "title.mp4"
    end_mp4 = TEMP_DIR / "end.mp4"
    _img_to_mp4(title_png, title_mp4, title_dur, out_w, out_h, fade="in")
    _img_to_mp4(end_png, end_mp4, end_dur, out_w, out_h, fade="out")

    # Step 3: Concat demuxer (all same codec/resolution)
    concat_file = TEMP_DIR / "concat.txt"
    concat_file.write_text(
        f"file '{title_mp4.name}'\n"
        f"file '{video_mp4.name}'\n"
        f"file '{end_mp4.name}'\n"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_mp4),
    ])


# ── Desktop demo recording ────────────────────────────────────────────────

def perform_desktop_journey(browser, base_url: str) -> Path:
    """Record a full desktop user journey as a continuous video."""
    record_dir = TEMP_DIR / "desktop_rec"
    record_dir.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(
        viewport={"width": DESKTOP_W, "height": DESKTOP_H},
        device_scale_factor=1,
        record_video_dir=str(record_dir),
        record_video_size={"width": DESKTOP_W, "height": DESKTOP_H},
    )
    page = context.new_page()

    page.add_init_script("""
        localStorage.setItem('mimi-nox-lang', 'de');
        localStorage.setItem('mimi_nox_onboarded', '1');
    """)

    # Navigate and wait for app
    page.goto(f"{base_url}/index.html?qa=readme-demo", wait_until="domcontentloaded")
    page.wait_for_function("() => window._nox")
    page.wait_for_timeout(1200)

    # Let the viewer see the home screen
    page.wait_for_timeout(1500)

    # Click into chat input and type a prompt
    human_type(page, "#chat-input",
               "/write Schreibe eine kurze professionelle Terminverschiebung",
               delay=50)

    # Send
    human_click(page, "#send-btn", pause_after=0.5)

    # Wait for AI response to stream in
    page.wait_for_function(
        "() => document.body.innerText.includes('Terminverschiebung')",
        timeout=15000
    )
    page.wait_for_timeout(1500)

    # Scroll down to see more of the response
    human_scroll(page, -300, steps=20)
    page.wait_for_timeout(1000)

    # Open provider settings modal
    human_click(page, "#btn-provider-settings", pause_after=0.5)
    page.wait_for_selector("#provider-modal:not(.hidden)", timeout=5000)
    page.wait_for_timeout(2000)

    # Close provider modal
    human_click(page, "#provider-cancel-btn", pause_after=0.5)
    page.wait_for_timeout(500)

    # Open mobile pairing modal
    human_click(page, "#btn-mobile-pairing", pause_after=0.5)
    page.wait_for_selector("#mobile-qr-overlay:not(.hidden)", timeout=5000)
    page.wait_for_timeout(2000)

    # Close mobile pairing modal
    page.evaluate("document.getElementById('mobile-qr-close-btn').click()")
    page.wait_for_timeout(600)

    # Navigate to skills tab
    human_click(page, "#tab-skills", pause_after=0.5)
    page.wait_for_timeout(500)
    page.wait_for_selector("#skill-chips", timeout=5000)
    page.wait_for_timeout(2000)

    # Scroll skills into view
    human_scroll(page, -200, steps=15)
    page.wait_for_timeout(1000)

    # Close page to finalize video recording
    page.close()
    context.close()

    # Find the .webm file
    webm_files = list(record_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No .webm recording found after desktop journey")
    return webm_files[0]


# ── Mobile demo recording ─────────────────────────────────────────────────

def perform_mobile_journey(browser, base_url: str) -> Path:
    """Record a full mobile user journey as a continuous video."""
    record_dir = TEMP_DIR / "mobile_rec"
    record_dir.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(
        viewport={"width": MOBILE_V_W, "height": MOBILE_V_H},
        device_scale_factor=1,
        is_mobile=True,
        has_touch=True,
        record_video_dir=str(record_dir),
        record_video_size={"width": MOBILE_V_W, "height": MOBILE_V_H},
    )
    page = context.new_page()

    page.add_init_script("localStorage.setItem('mimi-nox-lang', 'de');")

    # Navigate and wait for app
    page.goto(f"{base_url}/mobile.html?qa=readme-mobile-demo", wait_until="domcontentloaded")
    page.wait_for_selector("#input", timeout=10000)
    page.wait_for_timeout(1000)

    # Let the viewer see the mobile home
    page.wait_for_timeout(1200)

    # Click a skill chip
    human_click(page, '.skill-chip[data-trigger="/write"]', pause_after=0.5)
    page.wait_for_timeout(800)

    # Type a message
    human_type(page, "#input",
               "Antworte kurz: MiMi Nox ist jetzt am Handy verbunden",
               delay=55)

    # Send
    human_click(page, "#send-btn", pause_after=0.5)

    # Wait for AI response
    page.wait_for_function(
        "() => document.body.innerText.includes('Handy verbunden')",
        timeout=15000
    )
    page.wait_for_timeout(1500)

    # Scroll through the chat
    human_scroll(page, -300, steps=20)
    page.wait_for_timeout(1200)

    # Close page to finalize video
    page.close()
    context.close()

    webm_files = list(record_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No .webm recording found after mobile journey")
    return webm_files[0]


# ── Main pipeline ─────────────────────────────────────────────────────────

def main() -> None:
    start_time = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old temp recordings
    import shutil
    for old_dir in TEMP_DIR.iterdir():
        if old_dir.is_dir():
            shutil.rmtree(old_dir)
        else:
            old_dir.unlink()

    print("=" * 60)
    print("  MiMi Nox Demo Video Generator v3 (screen recording)")
    print("=" * 60)

    with static_server() as base_url, sync_playwright() as p:
        browser = p.chromium.launch()

        # ── Desktop Recording ─────────────────────────────────────────
        print(f"\n[1/4] Recording desktop demo ({DESKTOP_W}x{DESKTOP_H})...")
        t0 = time.time()
        desktop_webm = perform_desktop_journey(browser, base_url)
        print(f"  -> {desktop_webm.name} in {time.time()-t0:.1f}s")

        # ── Mobile Recording ──────────────────────────────────────────
        print(f"\n[2/4] Recording mobile demo ({MOBILE_V_W}x{MOBILE_V_H})...")
        t0 = time.time()
        mobile_webm = perform_mobile_journey(browser, base_url)
        print(f"  -> {mobile_webm.name} in {time.time()-t0:.1f}s")

        browser.close()

        # ── Compose Desktop Video ─────────────────────────────────────
        print("\n[3/4] Composing desktop video with title/end cards...")
        title_card = make_title_card("MiMi Nox", "Offline-first local AI assistant")
        end_card = make_end_card("MimiTechAi/mimi-nox")
        desktop_video = OUT_DIR / "mimi-nox-demo.mp4"

        compose_video_mp4(
            title_card, desktop_webm, end_card, desktop_video,
            title_dur=3.0, end_dur=2.0
        )

        if desktop_video.exists() and desktop_video.stat().st_size > 0:
            size_mb = desktop_video.stat().st_size / 1024 / 1024
            print(f"  -> {desktop_video.name} ({size_mb:.1f} MB)")
        else:
            print(f"  [WARN] {desktop_video.name} is empty or missing")

        # ── Compose Mobile Video ──────────────────────────────────────
        print("  Composing mobile video with QR intro + end card...")
        mobile_intro = make_mobile_qr_intro()
        mobile_end = make_end_card("MimiTechAi/mimi-nox",
                                   width=MOBILE_V_W, height=MOBILE_V_H)
        mobile_video = OUT_DIR / "mimi-nox-mobile-qr-demo.mp4"

        compose_video_mp4(
            mobile_intro, mobile_webm, mobile_end, mobile_video,
            title_dur=3.0, end_dur=2.0
        )

        if mobile_video.exists() and mobile_video.stat().st_size > 0:
            size_mb = mobile_video.stat().st_size / 1024 / 1024
            print(f"  -> {mobile_video.name} ({size_mb:.1f} MB)")
        else:
            print(f"  [WARN] {mobile_video.name} is empty or missing")

        # ── Cleanup temp ──────────────────────────────────────────────
        for old_dir in TEMP_DIR.iterdir():
            if old_dir.is_dir():
                shutil.rmtree(old_dir)
            else:
                old_dir.unlink()

        elapsed = time.time() - start_time
        print(f"\n{'=' * 60}")
        print(f"  Done in {elapsed:.1f}s")
        print(f"  Desktop: {desktop_video}")
        print(f"  Mobile:  {mobile_video}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    start = time.time()
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    else:
        print(f"Total: {time.time() - start:.1f}s")
