"""P0-2 Smoke: e2e-AI-Tests gegen den DGX-Spark-vLLM-Endpoint (Qwen3.8-27B NVFP4).

Warum: Der Mac (16GB) kann kein Ollama-Modell für e2e-AI-Tests betreiben.
SPECK-ADDENDUM (CTO): alle e2e-AI-Tests laufen gegen den verbundenen
DGX-Spark-vLLM-Server statt Ollama-Pull.

Test-Regeln (CTO-freigegeben, 2026-08-18):
- EIN HTTP-Client pro Test-Datei (Session-Wiederverwendung, kein fresh-Connect pro Test).
- Sampling fixgepinnt: `max_tokens=20`, `temperature=0.6`, `top_p=0.95` → schnell + reproduzierbar.
  (temperature>0 → nicht exakt deterministisch: Reproduzierbarkeit über Leading-Word-Majority prüfen.)
- `enable_thinking=false` (chat_template_kwargs): qwen38-27b ist Reasoning-Modell,
  ohne das Flag frisst Thinking das 20-Token-Budget und content=null (gemessen 2026-08-18).
- Endpoint unerreichbar → SKIP (kein Fake-Green), mit Evidenz-Grund.

Voraussetzung: Tailnet-Reachability von
    http://spark-2c73.tail8f685e.ts.net:8000/v1
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

DGX_BASE = os.environ.get("MIMI_NOX_DGX_BASE", "http://spark-2c73.tail8f685e.ts.net:8000/v1")
QWEN_MODEL = "qwen38-27b-unsloth-nvfp4"

# ── Ein Client pro Test-Datei (HTTP ist stateless: eine Verbindung + Timeout) ──
_TIMEOUT_S = int(os.environ.get("MIMI_NOX_DGX_TIMEOUT_S", "120"))


class _DgxClient:
    """Minimaler stateless-Client gegen den OpenAI-konformen vLLM-Endpoint."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_models(self) -> list[str]:
        req = urllib.request.Request(f"{self.base}/models", method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m["id"] for m in data.get("data", [])]

    def complete(self, prompt: str, max_tokens: int = 20,
                 temperature: float = 0.6, top_p: float = 0.95) -> str:
        """Completion mit CTO-fixgepinnten Sampling-Werten (2026-08-18):
        max_tokens=20, temperature=0.6, top_p=0.95 → schnell + reproduzierbar.

        Root-Cause (gemessen 2026-08-18): qwen38-27b ist ein Reasoning-Modell —
        ohne `enable_thinking=false` frisst das Thinking-Budget die 20 Tokens
        und `content` kommt als null zurück. Mit dem Flag: content='ok' in
        0.7s (completion_tokens=2).
        """
        data = self._post(
            "/chat/completions",
            {
                "model": QWEN_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,   # fixgepinnt (SPECK-Regel, CTO-Freigabe)
                "temperature": temperature,  # fixgepinnt
                "top_p": top_p,              # fixgepinnt
                # Reasoning-Modell: Thinking abschalten, damit das Token-Budget
                # für den Output gilt (sonst content=null bei max_tokens=20).
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        content = data["choices"][0]["message"]["content"]
        if content is None:
            raise AssertionError(
                "content=null trotz enable_thinking=false — Reasoning frisst "
                f"nach wie vor das Token-Budget. usage={data.get('usage')!r}"
            )
        return content


# Ein Client für die ganze Datei.
client = _DgxClient(DGX_BASE)


def _endpoint_reachable() -> bool:
    try:
        client.get_models()
        return True
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


pytestmark = pytest.mark.skipif(
    not _endpoint_reachable(),
    reason=f"DGX-Spark-Endpoint {DGX_BASE} nicht erreichbar (Tailnet?) — SKIP, kein Fake-Green.",
)


def test_smoke_v1_models_contains_qwen():
    """/v1/models liefert das erwartete Modell (Pinning, keine Abweichung)."""
    models = client.get_models()
    assert QWEN_MODEL in models, f"erwartet {QWEN_MODEL!r}, gefunden: {models!r}"


def test_smoke_completion_returns_content():
    """Eine Completion (CTO-Pin: max_tokens=20, temperature=0.6, top_p=0.95,
    enable_thinking=false) liefert nicht-leeren Content.
    Evidenz-Baseline: 1 Call ≈ 0.7s real (2026-08-18)."""
    content = client.complete("Antworte mit exakt einem Wort: ok")
    assert isinstance(content, str)
    assert content.strip(), f"leere Completion: {content!r}"


def test_smoke_completion_is_reproducible_under_pinned_sampling():
    """Unter CTO-Pin (temperature=0.6, top_p=0.95) ist die Ausgabe nicht exakt
    deterministisch — aber reproduzierbar: ≥2/3 identicaler Calls stimmen auf
    dem Leading-Word überein. Verifiziert das Pin statt exakte Gleichheit
    (sonst flaky bei temperature>0)."""
    def leading_word(s: str) -> str:
        toks = [t for t in s.replace("\n", " ").split() if t.strip()]
        return toks[0].lower().strip(".,!?") if toks else ""

    samples = [leading_word(client.complete("Antworte mit exakt einem Wort: ok"))
               for _ in range(3)]
    samples = [s for s in samples if s]
    assert samples, f"keine nicht-leeren Samples: {samples!r}"
    from collections import Counter
    top, count = Counter(samples).most_common(1)[0]
    assert count >= 2, f"Reproduzierbarkeit unter Pin verletzt: {samples!r} (majority {top!r} ×{count})"
