"""CI Perf-Regression-Gates (Phase 4 Item 17 + Phase 1 Item 5).

Prinzip (Brief): TOLERANZ-GATES, keine absoluten Zeiten — flaky-frei durch
  1. Warmup-Runde vor jeder Messung (Interpreter/Imports/Server-Boot),
  2. Budget = Baseline + großzügige Toleranz für langsame CI-Runner,
  3. Skip-Möglichkeit via MIMI_NOX_BENCH_GATE=0 (Debugging).

Messwerte:
  - Startup (CLI `--version`): Baseline p50 = 60ms lokal (Phase 1 DoD,
    2026-08-13, /usr/bin/time, 7 Läufe). Budget 150ms (100ms + 50% Toleranz).
  - TTFB (time-to-first-token, SSE-Stream): Fake-Provider mit 50ms/Token
    Latenz + echtem uvicorn-Server (Pattern aus test_serve_openai.py /
    test_jcode_e2e.py). Erwartung ~50-55ms. Budget 500ms (3x Toleranz).

Deterministik: Fake-Latenz via asyncio.sleep (kein echter LLM), WARMUP-Runde
vor der Messung. TTFB läuft über pytest-benchmark (JSON-Report via
--benchmark-json nach .benchmarks/, gitignored).
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

import httpx
import pytest
import uvicorn

from server.openai import create_openai_app

# ---------------------------------------------------------------------------
# Konstanten (Toleranz-Gates, Beleg in Modul-Doctstring oben)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

# Baseline p50=60ms lokal (2026-08-13) → Budget 150ms (100ms + 50% CI-Toleranz)
STARTUP_BUDGET_S = 0.150
# TTFB mit Fake-Latenz 50ms/Token → Erwartung ~55ms → Budget 500ms (3x Toleranz)
TTFB_BUDGET_S = 0.500
# Fake-Latenz pro Token (asyncio.sleep, kein echter LLM)
TOKEN_LATENCY_S = 0.05
N_CHUNKS = 3
N_MEASURE_RUNS = 5

# Skip-Schalter (Brief: MIMI_NOX_BENCH_GATE=0 für Debugging)
BENCH_GATE_ENABLED = os.environ.get("MIMI_NOX_BENCH_GATE", "1") != "0"
pytestmark = pytest.mark.skipif(
    not BENCH_GATE_ENABLED,
    reason="MIMI_NOX_BENCH_GATE=0 → Bench-Gates deaktiviert (Debugging)",
)


# ---------------------------------------------------------------------------
# Startup-Messung (CLI `--version` via subprocess — der echte End-to-End-Startup)
# ---------------------------------------------------------------------------
def _run_cli_version() -> float:
    """Misst die Echtzeit für `miminox_cli.py --version` (Interpreter+Imports+Parse).

    Liefert Sekunden. `--version` druckt die Version und exit 0 — braucht keinen
    Ollama/Provider, daher offline-sicher (CI: MIMI_NOX_MODEL=mock).
    """
    t0 = time.perf_counter()
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "miminox_cli.py"), "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
        env={**os.environ, "MIMI_NOX_OFFLINE": "1", "MIMI_NOX_MODEL": "mock"},
    )
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# TTFB-Messung (SSE-Stream mit konfigurierbarer Token-Latenz, echtem uvicorn)
# ---------------------------------------------------------------------------
class LatencyFakeClient:
    """Fake-Provider: N Chunks mit konfigurierbarer Latenz (asyncio.sleep).

    Kein echter LLM — deterministisch. `chat(..., stream=True)` liefert einen
    AsyncIterator (Pattern aus tests/test_serve_openai.py).
    """

    def chat(self, model, messages, stream):  # noqa: ARG002
        async def _gen():
            for i in range(N_CHUNKS):
                await asyncio.sleep(TOKEN_LATENCY_S)
                yield {"message": {"content": f"tok{i}"}}

        return _gen()


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_ready(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as resp:  # noqa: S310
                if resp.status == 200:
                    return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.1)
    raise AssertionError(f"Engine nicht bereit auf Port {port}")


@pytest.fixture
def engine_base_url():
    """Startet die serve-Engine als echten uvicorn-Server mit Latenz-Fake.

    Wird NUR EINMAL pro Test gestartet; die gemessene Funktion (TTFB) läuft
    dagegen wiederholt gegen dieselbe Instanz. Teardown stoppt den Server.
    """
    port = _free_port()
    patcher = patch(
        "server.openai.build_provider_client",
        lambda *a, **k: LatencyFakeClient(),
    )
    patcher.start()
    app = create_openai_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)
    base = f"http://127.0.0.1:{port}"
    try:
        yield base
    finally:
        patcher.stop()
        server.should_exit = True
        thread.join(timeout=5)


async def _ttfb_once(base: str) -> float:
    """Misst time-to-first-token: Zeit bis zum ersten SSE-Data-Event (Sekunden)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        t0 = time.perf_counter()
        async with client.stream(
            "POST",
            f"{base}/v1/chat/completions",
            json={
                "model": "gemma4:12b",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        ) as resp:
            assert resp.status_code == 200, f"Stream-Status {resp.status_code}"
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    ttfb = time.perf_counter() - t0
                    # Validierung: das First-Event ist ein echtes Delta
                    payload = json.loads(line[len("data: "):])
                    payload["choices"][0]["delta"]
                    return ttfb
    raise AssertionError("Kein First-Data-Event empfangen")


def _ttfb_sync(base: str) -> float:
    return asyncio.run(_ttfb_once(base))


# ---------------------------------------------------------------------------
# Gate-Tests
# ---------------------------------------------------------------------------
def test_startup_budget(benchmark):
    """Gate: CLI-Startup (`--version`) mean < 150ms (Baseline p50=60ms, 2026-08-13).

    Design (flaky-frei):
      1. Warmup-Runde NICHT gemessen (Interpreter/Imports warm),
      2. ``benchmark()`` dient NUR dem JSON-Report (.benchmarks/, gitignored) —
         mit ``--benchmark-disable`` läuft die Funktion einfach einmal weiter,
         das Gate selbst ist davon entkoppelt,
      3. Das GATE ist eine manuelle Mittelwert-Messung (N_MEASURE_RUNS Läufe),
         robust gegen Ausreißer und in jedem pytest-benchmark-Modus identisch.
    """
    _run_cli_version()  # Warmup (nicht gemessen)

    # JSON-Report (entkoppelt vom Gate — läuft auch bei --benchmark-disable)
    benchmark(_run_cli_version)

    # GATE: manuelle, deterministische Messung
    runs = [_run_cli_version() for _ in range(N_MEASURE_RUNS)]
    runs.sort()
    p50 = runs[len(runs) // 2]
    mean = sum(runs) / len(runs)
    print(f"\n  [startup] p50={p50 * 1000:.1f}ms mean={mean * 1000:.1f}ms  "
          f"(Budget {STARTUP_BUDGET_S * 1000:.0f}ms)")
    assert mean < STARTUP_BUDGET_S, (
        f"Startup-Regression: mean {mean * 1000:.1f}ms > Budget "
        f"{STARTUP_BUDGET_S * 1000:.0f}ms (Baseline p50=60ms, 2026-08-13)"
    )


def test_ttfb_budget(benchmark, engine_base_url):
    """Gate: TTFB (time-to-first-token) mean < 500ms (Fake-Latenz 50ms/Token).

    Der uvicorn-Server läuft bereits (engine_base_url-Fixtur). Wie test_startup_budget:
    ``benchmark()`` nur als JSON-Report, das GATE ist eine manuelle Messung
    (N_MEASURE_RUNS Läufe, Warmup vorher) → deterministisch in jedem Modus.
    """
    base = engine_base_url
    _ttfb_sync(base)  # Warmup: erste Anfrage (Handshake, nicht gemessen)

    # JSON-Report (entkoppelt vom Gate)
    benchmark(lambda: _ttfb_sync(base))

    # GATE: manuelle, deterministische Messung
    runs = [_ttfb_sync(base) for _ in range(N_MEASURE_RUNS)]
    runs.sort()
    p50 = runs[len(runs) // 2]
    mean = sum(runs) / len(runs)
    print(f"\n  [ttfb] p50={p50 * 1000:.1f}ms mean={mean * 1000:.1f}ms  "
          f"(Budget {TTFB_BUDGET_S * 1000:.0f}ms)")
    assert mean < TTFB_BUDGET_S, (
        f"TTFB-Regression: mean {mean * 1000:.1f}ms > Budget "
        f"{TTFB_BUDGET_S * 1000:.0f}ms (Fake-Latenz {TOKEN_LATENCY_S * 1000:.0f}ms/Token)"
    )


def test_ttfb_deterministic_within_tolerance(engine_base_url):
    """Sanity: TTFB bleibt stabil (Spread < Budget) — kein Flakiness-Signal.

    N_MESURE_RUNS Läufe, max < Budget. Fängt systematische Latenzsprünge ab,
    ohne auf exakte Zeiten zu pochen.
    """
    base = engine_base_url
    _ttfb_sync(base)  # Warmup
    runs = sorted(_ttfb_sync(base) for _ in range(N_MEASURE_RUNS))
    p50 = runs[len(runs) // 2]
    worst = runs[-1]
    print(f"\n  [ttfb-spread] p50={p50 * 1000:.1f}ms worst={worst * 1000:.1f}ms")
    assert worst < TTFB_BUDGET_S, f"TTFB-Spread zu groß: worst {worst * 1000:.1f}ms"
