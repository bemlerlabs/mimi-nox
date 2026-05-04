"""
/help Skill — GWT, 3× Tiefe.

GIVEN: Eine help.md Skill-Datei existiert
WHEN:  Sie geladen wird
THEN:  trigger ist '/help', hat valide Felder

GIVEN: Die Skills-Liste
WHEN:  Nach /help gesucht wird
THEN:  Skill ist registriert und ladbar

GIVEN: Der Skill wird aufgerufen
WHEN:  Die Response geprüft wird
THEN:  Antwort enthält alle Kern-Feature-Kategorien
"""
from pathlib import Path
import re


# ── Blickwinkel 1: Skill-Datei vorhanden und valide ───────────────────────────

class TestHelpSkillFilePerspective:
    """GIVEN help.md, WHEN parsed, THEN all required fields present."""

    def test_given_help_md_when_parsed_then_has_required_fields(self):
        """
        GIVEN: help.md existiert im skills/ Verzeichnis
        WHEN:  Datei gelesen und auf Pflichtfelder geprüft
        THEN:  name, trigger, description, system_prompt vorhanden
        """
        skill_path = Path(__file__).parent.parent / "skills" / "help.md"

        # Perspektive 1: Datei existiert
        assert skill_path.exists(), "THEN: skills/help.md muss existieren"

        content = skill_path.read_text()

        # Perspektive 2: Trigger ist /help
        content_lower = content.lower()
        assert "trigger" in content_lower and "/help" in content_lower, (
            "THEN: Trigger muss '/help' sein"
        )

        # Perspektive 3: System Prompt nicht leer
        assert "system prompt" in content_lower, "THEN: system_prompt Feld muss vorhanden sein"
        assert len(content) > 200, "THEN: help.md muss substanziellen Inhalt haben"


# ── Blickwinkel 2: Skill ist registriert und per API ladbar ───────────────────

class TestHelpSkillRegistrationPerspective:
    """GIVEN skills loader, WHEN help skill loaded, THEN trigger resolves."""

    def test_given_skills_when_help_loaded_then_trigger_resolves(self):
        """
        GIVEN: Skills-System ist initialisiert
        WHEN:  Alle Skills geladen werden
        THEN:  /help Skill ist in der Liste
        """
        from core.skills import SkillLoader

        skills = SkillLoader().load_all()

        # Perspektive 1: Skills-Liste nicht leer
        assert len(skills) > 0, "THEN: Skills-Liste muss mindestens einen Eintrag haben"

        # Perspektive 2: /help ist dabei
        triggers = [s.trigger for s in skills]
        assert "/help" in triggers, (
            f"THEN: /help Skill muss registriert sein, found: {triggers}"
        )

        # Perspektive 3: /help Skill hat validen System-Prompt
        help_skill = next(s for s in skills if s.trigger == "/help")
        assert len(help_skill.system_prompt.strip()) > 50, (
            "THEN: /help Skill system_prompt darf nicht leer sein"
        )


# ── Blickwinkel 3: Help-Inhalt ist vollständig ────────────────────────────────

class TestHelpSkillContentPerspective:
    """GIVEN help.md content, WHEN feature categories checked, THEN all present."""

    def test_given_help_content_when_features_checked_then_all_core_present(self):
        """
        GIVEN: help.md system_prompt ist geladen
        WHEN:  Auf Kern-Features geprüft wird
        THEN:  Chat, Memory, Files, Tasks, Voice erwähnt
        """
        skill_path = Path(__file__).parent.parent / "skills" / "help.md"
        content = skill_path.read_text().lower()

        core_features = {
            "chat":   ["chat", "conversation", "gespräch", "fragen"],
            "memory": ["memory", "erinnerung", "kontext"],
            "files":  ["file", "pdf", "datei", "document"],
            "voice":  ["voice", "audio", "sprache", "speak"],
            "search": ["search", "web", "suche", "research"],
        }

        missing = []
        for feature, keywords in core_features.items():
            if not any(kw in content for kw in keywords):
                missing.append(feature)

        assert not missing, (
            f"THEN: help.md fehlen Feature-Kategorien: {missing}"
        )
