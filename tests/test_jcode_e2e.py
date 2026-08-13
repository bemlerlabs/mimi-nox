"""
◑ MiMi Nox – Phase 3 Item 14: JCode/Codex/OpenCode als Consumer der Engine (e2e)
tests/test_jcode_e2e.py

Beweist den OpenAI-Interop-Nachweis: Ein echtes Coding-CLI-Binary (jcode, Rust)
konsumiert die lokale MiMi Nox serve-Engine über deren /v1-API.

Deterministisch & offline:
  - Die Engine läuft mit einem Fake-Backend (kein echtes Ollama/DS4 nötig).
    Der Fake-Client liefert immer "Hello from the Black Forest".
  - jcode wird mit einem temp $HOME isoliert (schreibt $HOME/.jcode/config.toml,
    die User-Config bleibt unberührt) und als OpenAI-compatibles Profil auf die
    lokale Engine gerichtet (jcode provider add mimi-nox).
  - jcode run → Antwort muss den Fake-Engine-Inhalt enthalten → Beweis, dass die
    Antwort von der MiMi Nox Engine kam, nicht von einem echten Modell.

Skip wenn jcode nicht installiert ist (CI-freundlich, wie die Ollama-Skips).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch
from urllib.request import urlopen

import pytest
import uvicorn

from server.openai import create_openai_app

CHUNKS = ["Hello", " from", " the", " Black", " Forest"]
FULL = "".join(CHUNKS)

pytestmark = pytest.mark.skipif(
    shutil.which("jcode") is None, reason="jcode (Rust coding CLI) nicht installiert"
)


class FakeClient:
    """Ersetzt build_provider_client: liefert immer die gleiche Engine-Antwort."""

    def chat(self, model, messages, stream):  # noqa: ARG002
        async def _gen():
            for chunk in CHUNKS:
                yield {"message": {"content": chunk}}

        return _gen()


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_ready(port: int, timeout: float = 15.0) -> None:
    """Pollt bis der /v1/models-Endpunkt der Engine antwortet."""
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as resp:  # noqa: S310
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(0.1)
    raise AssertionError(f"Engine nicht bereit auf Port {port}: {last_err}")


def _start_engine(port: int):
    """Startet die serve-Engine als echten uvicorn-Server mit Fake-Backend."""
    # Modul-Attribut patchen → wirkt thread-übergreifend (Engine läuft im Thread).
    patcher = patch("server.openai.build_provider_client", lambda *a, **k: FakeClient())
    patcher.start()
    app = create_openai_app()  # kein Token → nur localhost-Bind

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)
    return server, thread, patcher


def _jcode(args, home: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = home  # jcode liest $HOME/.jcode → temp, User-Config bleibt sauber
    return subprocess.run(
        ["jcode", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _contains_engine_marker(text: str) -> bool:
    """jcode-Antwort rekursiv nach dem Fake-Engine-Marker durchsuchen."""
    if "Black Forest" in text:
        return True
    try:
        return _walk(json.loads(text))
    except Exception:  # noqa: BLE001
        return False


def _walk(node) -> bool:
    if isinstance(node, str):
        return "Black Forest" in node
    if isinstance(node, dict):
        return any(_walk(v) for v in node.values())
    if isinstance(node, list):
        return any(_walk(v) for v in node)
    return False


def test_jcode_consumes_engine_e2e():
    """jcode (Rust Coding CLI) konsumiert die MiMi Nox Engine als OpenAI-Consumer."""
    port = _free_port()
    server, server_thread, patcher = _start_engine(port)
    tmp_home = tempfile.mkdtemp(prefix="jcode-e2e-")
    try:
        base_url = f"http://127.0.0.1:{port}/v1"

        # 1) jcode als OpenAI-compatibles Profil auf die lokale Engine richten
        add = _jcode(
            [
                "provider",
                "add",
                "mimi-nox",
                "--base-url",
                base_url,
                "--model",
                "gemma4:12b",
                "-p",
                "openai-compatible",
            ],
            tmp_home,
        )
        assert add.returncode == 0, f"provider add fehlgeschlagen:\n{add.stderr}"

        # 2) Ein echter `run` gegen die Engine
        run = _jcode(
            ["run", "Antworte in einem Wort: Wo liegt der Schwarzwald?", "--provider-profile", "mimi-nox", "--json"],
            tmp_home,
        )
        assert run.returncode == 0, f"jcode run fehlgeschlagen:\n{run.stderr}"

        # 3) Beweis: Die Antwort kam von der MiMi Nox Engine (Fake-Marker), nicht
        #    von einem echten/remote Modell.
        assert _contains_engine_marker(run.stdout), (
            "jcode-Antwort enthält nicht den Engine-Marker 'Black Forest' — "
            "Antwort kam nicht von der lokalen MiMi Nox Engine.\n"
            f"stdout: {run.stdout[:500]}\nstderr: {run.stderr[:500]}"
        )
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
        patcher.stop()
        shutil.rmtree(tmp_home, ignore_errors=True)
