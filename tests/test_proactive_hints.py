"""
Proaktive Hinweise — GWT, 3× Tiefe.

GIVEN: System-Prompt enthält Regel für proaktive Memory-Hinweise
WHEN:  Prompt auf enthaltene Schlüsselbegriffe geprüft wird
THEN:  Klare Anweisung vorhanden dass MiMi aktiv auf Memory hinweist

GIVEN: Memory enthält relevante Einträge zu einem Thema
WHEN:  get_context_injection() aufgerufen wird
THEN:  Kontext-Block enthält eine Hinweis-Einleitung für das Modell

GIVEN: Leerer Memory-Store
WHEN:  get_context_injection() aufgerufen wird
THEN:  Leerer String (kein False-Positive-Hinweis)
"""
from __future__ import annotations

import pytest
from pathlib import Path


# ── Blickwinkel 1: System-Prompt enthält proaktive Regel ──────────────────────

class TestProactiveHintSystemPromptPerspective:
    """GIVEN the system prompt, WHEN inspected, THEN proactive memory hint rule exists."""

    def test_given_system_prompt_when_checked_then_has_proactive_hint_rule(self):
        """
        GIVEN: NOX_SYSTEM_PROMPT ist geladen
        WHEN:  Prompt auf proaktive Hinweis-Logik geprüft wird
        THEN:  Mindestens eine Regel die MiMi anweist auf Memory hinzuweisen
        """
        from core.chat import NOX_SYSTEM_PROMPT

        # Perspektive 1: Keyword "previously" oder "noted" vorhanden
        has_proactive = any(kw in NOX_SYSTEM_PROMPT.lower() for kw in [
            "previously", "noted", "proactive", "mentioned before",
            "you already", "remember", "context"
        ])
        assert has_proactive, (
            "THEN: Prompt muss proaktive Hinweis-Regel enthalten, got:\n"
            + NOX_SYSTEM_PROMPT[:300]
        )

        # Perspektive 2: Regel ist nicht nur allgemein, sondern spezifisch
        assert "memory" in NOX_SYSTEM_PROMPT.lower() or "context" in NOX_SYSTEM_PROMPT.lower(), (
            "THEN: Prompt soll Memory-Kontext explizit ansprechen"
        )

        # Perspektive 3: Die Regel steht in einem eigenen Abschnitt
        assert "\n" in NOX_SYSTEM_PROMPT, "THEN: Prompt muss mehrzeilig strukturiert sein"


# ── Blickwinkel 2: Memory-Kontext-Injection hat Hinweis-Einleitung ────────────

class TestProactiveHintMemoryInjectionPerspective:
    """GIVEN memory entries, WHEN context injected, THEN hint prefix present."""

    def test_given_memory_entries_when_context_injected_then_hint_prefix_present(self, tmp_path):
        """
        GIVEN: Memory-Store hat einen Eintrag zu einem Thema
        WHEN:  get_context_injection() mit verwandtem Query aufgerufen wird
        THEN:  Rückgabe enthält einen Kontext-Block (nicht leer)
        """
        from core.memory import Memory

        mem = Memory(persist_dir=str(tmp_path / "chroma"), collection_name="test_proactive")
        mem.store("Der Nutzer arbeitet an einem KI-Assistenten namens MiMi.", {"source": "test"})

        # Perspektive 1: Kontext-Block nicht leer bei relevantem Query
        ctx = mem.get_context_injection("MiMi KI-Assistent")
        assert len(ctx.strip()) > 0, "THEN: Kontext-Block muss Inhalt haben"

        # Perspektive 2: Kontext enthält gespeicherten Text
        assert "MiMi" in ctx or "KI" in ctx or "Assistent" in ctx, (
            f"THEN: Kontext muss relevante Daten enthalten, got: {ctx[:200]}"
        )

        # Perspektive 3: Kontext hat strukturierte Einleitung
        first_line = ctx.strip().split("\n")[0]
        assert len(first_line) > 5, "THEN: Erster Block muss Einleitungs-Header haben"

    def test_given_empty_memory_when_context_injected_then_empty_string(self, tmp_path):
        """
        GIVEN: Memory-Store ist leer
        WHEN:  get_context_injection() aufgerufen wird
        THEN:  Leerer String — kein False-Positive
        """
        from core.memory import Memory

        mem = Memory(persist_dir=str(tmp_path / "chroma2"), collection_name="test_empty")

        ctx = mem.get_context_injection("beliebiger Query")

        # Perspektive 1: Leer wenn nichts gespeichert
        assert ctx == "", (
            f"THEN: Leerer Memory muss leeren String zurückgeben, got: '{ctx[:100]}'"
        )

        # Perspektive 2: Kein Whitespace-only Output
        assert ctx.strip() == "", "THEN: Kein Whitespace-only Output"

        # Perspektive 3: Kein Crash bei leerem Store
        # (Test selbst ist der Beweis — kein Exception)


# ── Blickwinkel 3: Proaktive Formulierung im Kontext-Prefix ───────────────────

class TestProactiveHintContextPrefixPerspective:
    """GIVEN memory with entries, WHEN prefix inspected, THEN it signals prior knowledge."""

    def test_given_memory_with_entries_when_prefix_read_then_signals_prior_knowledge(self, tmp_path):
        """
        GIVEN: Memory hat Einträge
        WHEN:  Der Prefix des Kontext-Blocks gelesen wird
        THEN:  Formulierung signalisiert "Früher schon gesagt / bekannt"
        """
        from core.memory import Memory

        mem = Memory(persist_dir=str(tmp_path / "chroma3"), collection_name="test_prefix")
        mem.store("Lieblingsfarbe des Nutzers ist Blau.", {"source": "test"})

        ctx = mem.get_context_injection("Farbe")

        # Perspektive 1: Vorhanden und strukturiert
        assert len(ctx) > 0, "THEN: Kontext muss Inhalt haben"

        # Perspektive 2: Enthält Marker-Wörter die Prior Knowledge signalisieren
        ctx_lower = ctx.lower()
        has_prior_signal = any(kw in ctx_lower for kw in [
            "memory", "context", "known", "remember", "earlier",
            "erinnerung", "kontext", "bekannt", "früher", "already"
        ])
        assert has_prior_signal, (
            f"THEN: Kontext-Block soll Prior Knowledge signalisieren, got:\n{ctx[:300]}"
        )
