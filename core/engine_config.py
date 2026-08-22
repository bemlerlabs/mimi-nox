"""
◑ MiMi Nox – Engine Configuration Persistence
core/engine_config.py

Persistiert die Engine-Auswahl der CLI/TUI (`miminox tui`), damit ein User
seine Engine (lokale Ollama / eigene Ollama- oder vLLM-Engine / DGX-Spark ds4 /
OpenAI-kompatible API) nur einmal wählt und bei jedem Start ohne Modell-Flag
wiederverwendet wird ("hinterlegen").

Konvention:
- Provider-Enum: local_ollama | custom_ollama | openai_compatible
  (deckungsgleich mit core/model_provider.py).
- API-Keys werden NIEMALS nach ~/.mimi-nox/engine.json geschrieben. Ein
  optional eingegebener Key wird nur als Session-Env gesetzt und vom
  Provider-System (MIMI_OPENAI_COMPAT_API_KEY) gelesen.
- api_url ist die volle OpenAI-kompatible Basis-URL (z.B. http://spark-...:8000/v1).

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

# ── Provider-Konstanten (deckungsgleich mit core/model_provider.py) ──────────
LOCAL_OLLAMA = "local_ollama"
CUSTOM_OLLAMA = "custom_ollama"
OPENAI_COMPAT = "openai_compatible"

VALID_PROVIDERS = (LOCAL_OLLAMA, CUSTOM_OLLAMA, OPENAI_COMPAT)

DEFAULT_LOCAL_MODEL = "gemma4:12b"
DEFAULT_DGX_MODEL = "deepseek-v4-flash"
# ── Mimi Tech AI Standard-Engine (User-Mandat 2026-08-18) ─────────────────
# Qwen 3.8 27B auf DGX Spark — Default-Engine, kein Ollama-Bundling/Download.
# Provider-Wahl (eigener Endpoint, Ollama, OpenRouter) = END-USER-Onboarding.
DEFAULT_DGX_SPARK_URL = "http://spark-2c73.tail8f685e.ts.net:8000/v1"
DEFAULT_DGX_SPARK_MODEL = "qwen3.8-27b"

def default_engine_choice() -> "EngineChoice":
    """Return the standard MiMi Nox engine: Qwen 3.8 27B on DGX Spark.
    
    Called when no persisted config exists and user hasn't passed
    --configure. The END-USER can override at onboarding (--configure)
    by choosing any OpenAI-compatible endpoint (Ollama, OpenRouter, custom).
    """
    return EngineChoice(
        provider=OPENAI_COMPAT,
        model=DEFAULT_DGX_SPARK_MODEL,
        api_url=DEFAULT_DGX_SPARK_URL,
    )


CONFIG_DIR = Path(os.environ.get("MIMI_NOX_CONFIG_DIR", str(Path.home() / ".mimi-nox")))
CONFIG_FILE = "engine.json"


@dataclass
class EngineChoice:
    """Unveränderliche, persistierbare Engine-Auswahl."""

    provider: str  # local_ollama | custom_ollama | openai_compatible
    model: str
    api_url: str | None = None

    def __post_init__(self) -> None:
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(f"Unbekannter Provider: {self.provider!r}")
        if not self.model.strip():
            raise ValueError("Modellname darf nicht leer sein.")

    def to_flags(self) -> list[str]:
        """CLI-Flags für `miminox main()` – Modell und Engine-URL."""
        flags = ["--model", self.model]
        if self.api_url:
            flags += ["--api-url", self.api_url]
        return flags

    def apply_env(self) -> None:
        """Setzt Session-Env-Variablen, die das Provider-System liest.

        Wichtig: ``MIMI_MODEL_PROVIDER`` wird gemäß ``self.provider`` gesetzt,
        damit der Server-Resolver (core.model_provider._provider_from_env) die
        konfigurierte Engine aufschlägt – statt stillschweigend auf
        ``local_ollama`` zurückzufallen. Ohne diesen Key nutzte die PWA nie die
        konfigurierte Engine (z. B. Qwen-DGX), sondern immer lokale Ollama.
        """
        os.environ["MIMI_MODEL_PROVIDER"] = self.provider
        os.environ["MIMI_NOX_MODEL"] = self.model
        if self.provider == OPENAI_COMPAT and self.api_url:
            os.environ["MIMI_OPENAI_COMPAT_BASE_URL"] = self.api_url
            # Der Provider-Resolver (core.model_provider._provider_from_env) liest
            # das Modell aus MIMI_OPENAI_COMPAT_MODEL – ohne diesen Key würde die
            # Engine "custom-model" melden, obwohl MIMI_NOX_MODEL korrekt ist.
            os.environ["MIMI_OPENAI_COMPAT_MODEL"] = self.model
        elif self.provider == CUSTOM_OLLAMA and self.api_url:
            os.environ["MIMI_CUSTOM_OLLAMA_BASE_URL"] = self.api_url


def default_config_path() -> Path:
    """Kanonischer Speicherort der Engine-Auswahl."""
    return CONFIG_DIR / CONFIG_FILE


def load_engine_config(path: Path | None = None) -> EngineChoice | None:
    """Lädt die persistierte Engine-Auswahl. None, wenn keine Konfig existiert."""
    cfg_path = path or default_config_path()
    try:
        if not cfg_path.exists():
            return None
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        return EngineChoice(
            provider=raw["provider"],
            model=raw["model"],
            api_url=raw.get("api_url"),
        )
    except Exception:
        # Beschädigte oder unlesbare Konfig → wie keine behandeln, nie crashen.
        return None


def save_engine_config(
    choice: EngineChoice, path: Path | None = None
) -> bool:
    """Persistiert die Engine-Auswahl atomar nach ~/.mimi-nox/engine.json."""
    cfg_path = path or default_config_path()
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        # Härtung (AppSec/Least-Privilege): Konfig-Verzeichnis nur für den Owner
        # (0700). Verhindert, dass andere lokale Prozesse die Engine-Auswahl lesen
        # oder Side-Channels auf die Konfig ziehen.
        try:
            cfg_path.parent.chmod(0o700)
        except OSError:
            pass
        payload = asdict(choice)
        tmp = cfg_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(cfg_path)
        # Härtung: engine.json nur für Owner les-/schreibbar (0600). Die Datei
        # selbst enthält nie Secrets (Keys bleiben Session-Env), aber Least-
        # Privilege gilt für jedes persistierte Artefakt.
        try:
            cfg_path.chmod(0o600)
        except OSError:
            pass
        return True
    except Exception:
        return False


def clear_engine_config(path: Path | None = None) -> bool:
    """Entfernt die persistierte Engine-Auswahl."""
    cfg_path = path or default_config_path()
    try:
        if cfg_path.exists():
            cfg_path.unlink()
        return True
    except Exception:
        return False
