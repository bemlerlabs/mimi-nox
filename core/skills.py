"""
◑ MiMi Nox – Skills System
core/skills.py

Lädt und testet Markdown-basierte Skills.

Skill-Format (Markdown):
  # skill-name
  **Trigger**: /trigger
  **Description**: Beschreibung
  **Tools**: tool1, tool2

  ## System Prompt
  Du bist ein...

  ## Test
  **Input**: Test-Eingabe
  **Expect Tool**: tool_name
  **Expect Contains**: erwarteter Text

Skill-Verzeichnisse (Priorität):
  1. ~/.mimi-nox/skills/     (Nutzer-Skills)
  2. skills/                 (Built-in Skills im Repo)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

DEFAULT_USER_SKILLS_DIR = Path.home() / ".mimi-nox" / "skills"
BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"
SKILL_CACHE_TTL_SECONDS = 60.0
_SKILL_LIST_CACHE: dict[tuple[str, str], tuple[float, list["Skill"]]] = {}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SkillTest:
    """Test-Definition innerhalb eines Skills."""
    input: str = ""
    expect_tool: str = ""
    expect_contains: str = ""


@dataclass
class Skill:
    """Geladenes Skill-Objekt."""
    name: str
    trigger: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    test: SkillTest = field(default_factory=SkillTest)
    when_to_use: list[str] = field(default_factory=list)
    when_not_to_use: list[str] = field(default_factory=list)
    quality_profile: str = "standard"
    artifact_types: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    has_references: bool = False
    reference_text: str = ""
    example_text: str = ""


@dataclass
class SkillTestResult:
    """Ergebnis eines Skill-Tests."""
    skill_name: str
    passed: bool
    message: str = ""
    tool_called: str = ""
    response: str = ""


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class SkillLoadError(Exception):
    """Skill-Datei ungültig oder nicht gefunden."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---", 4)
    if end == -1:
        return {}, content
    raw = content[4:end].strip()
    body = content[end + 4:].lstrip()
    meta: dict[str, object] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            values = meta.setdefault(current_key, [])
            if isinstance(values, list):
                values.append(line[4:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
            meta[current_key] = items
        elif value:
            meta[current_key] = value.strip("'\"")
        else:
            meta[current_key] = []
    return meta, body


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _read_supporting_text(skill_dir: Path, folder_name: str) -> tuple[bool, str, str]:
    reference_parts: list[str] = []
    example_parts: list[str] = []
    for rel, target in (("references", reference_parts), ("examples", example_parts)):
        directory = skill_dir / rel
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            target.append(f"# {folder_name}/{rel}/{path.name}\n{path.read_text(encoding='utf-8')}")
    return bool(reference_parts or example_parts), "\n\n".join(reference_parts), "\n\n".join(example_parts)


def _phrase_score(message: str, reference: str) -> int:
    stop = {
        "a", "an", "and", "the", "for", "with", "user", "asks", "ask", "use",
        "to", "of", "in", "my", "me", "please", "bitte", "und", "der", "die",
        "das", "für", "nur", "only",
    }
    message_words = set(re.findall(r"[a-zA-Z0-9_-]{3,}", message.lower())) - stop
    reference_words = set(re.findall(r"[a-zA-Z0-9_-]{3,}", reference.lower())) - stop
    return len(message_words & reference_words)


def _parse_skill(name: str, content: str, *, skill_dir: Path | None = None) -> Skill:
    """
    Parst eine Markdown-Skill-Datei.

    Raises:
        SkillLoadError: wenn Pflichtfelder fehlen
    """
    meta, body = _parse_frontmatter(content)

    # Trigger
    trigger_match = re.search(r"\*\*Trigger\*\*:\s*(\S+)", body)
    trigger = str(meta.get("trigger", "") or "").strip()
    if not trigger_match:
        if not trigger:
            raise SkillLoadError(
                f"Skill '{name}': Fehlendes Pflichtfeld '**Trigger**:'"
            )
    else:
        trigger = trigger_match.group(1).strip()

    # Description
    desc_match = re.search(r"\*\*Description\*\*:\s*(.+)", body)
    description = str(meta.get("description", "") or "").strip()
    if desc_match:
        description = desc_match.group(1).strip()

    # Tools
    tools_match = re.search(r"^\*\*Tools\*\*:[ \t]*(.*)$", body, re.MULTILINE)
    tools: list[str] = _as_list(meta.get("tools"))
    if tools_match:
        tools = [t.strip() for t in tools_match.group(1).split(",") if t.strip()]

    # System Prompt (zwischen ## System Prompt und ## Test oder Ende)
    sp_match = re.search(
        r"##\s+System Prompt\s*\n(.*?)(?=##|\Z)",
        body,
        re.DOTALL,
    )
    if not sp_match:
        raise SkillLoadError(
            f"Skill '{name}': Fehlender '## System Prompt' Block"
        )
    system_prompt = sp_match.group(1).strip()
    if not system_prompt:
        raise SkillLoadError(
            f"Skill '{name}': System Prompt ist leer"
        )

    # Test Block (optional)
    skill_test = SkillTest()
    test_block_match = re.search(r"##\s+Test\s*\n(.*?)(?:\Z)", body, re.DOTALL)
    if test_block_match:
        tb = test_block_match.group(1)
        inp = re.search(r"\*\*Input\*\*:\s*(.+)", tb)
        exp_tool = re.search(r"\*\*Expect Tool\*\*:\s*(\S+)", tb)
        exp_contains = re.search(r"\*\*Expect Contains\*\*:\s*(.+)", tb)

        skill_test = SkillTest(
            input=inp.group(1).strip() if inp else "",
            expect_tool=exp_tool.group(1).strip() if exp_tool else "",
            expect_contains=exp_contains.group(1).strip() if exp_contains else "",
        )

    has_references = False
    reference_text = ""
    example_text = ""
    if skill_dir:
        has_references, reference_text, example_text = _read_supporting_text(skill_dir, name)

    artifact_types = _as_list(meta.get("artifact_types"))
    if not artifact_types:
        lowered = f"{name} {trigger} {' '.join(tools)}".lower()
        artifact_types = [
            artifact
            for marker, artifact in (("pdf", "pdf"), ("svg", "svg"), ("chart", "chart"), ("deck", "deck"), ("presentation", "deck"))
            if marker in lowered
        ]

    return Skill(
        name=str(meta.get("name", name) or name),
        trigger=trigger,
        description=description,
        system_prompt=system_prompt,
        tools=tools,
        test=skill_test,
        when_to_use=_as_list(meta.get("when_to_use")),
        when_not_to_use=_as_list(meta.get("when_not_to_use")),
        quality_profile=str(meta.get("quality_profile", "") or ("artifact" if artifact_types else "standard")),
        artifact_types=artifact_types,
        allowed_tools=_as_list(meta.get("allowed_tools")) or list(tools),
        has_references=has_references,
        reference_text=reference_text,
        example_text=example_text,
    )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class SkillLoader:
    """
    Lädt Skills aus Markdown-Dateien.

    Sucht in:
      1. skills_dir (Nutzer-Skills, Standard: ~/.mimi-nox/skills/)
      2. BUILTIN_SKILLS_DIR (Built-in Skills im Repo)
    """

    def __init__(
        self,
        skills_dir: Path | None = None,
        builtin_dir: Path | None = None,
    ) -> None:
        self._user_dir = Path(skills_dir or DEFAULT_USER_SKILLS_DIR)
        self._builtin_dir = Path(builtin_dir or BUILTIN_SKILLS_DIR)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, name: str) -> Skill:
        """
        Lädt einen Skill per Name.

        Sucht: {name}.md in user_dir, dann builtin_dir.

        Raises:
            SkillLoadError: wenn Datei nicht gefunden oder ungültig
        """
        for directory in [self._user_dir, self._builtin_dir]:
            for path in [directory / f"{name}.md", directory / name / "SKILL.md"]:
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    skill_dir = path.parent if path.name == "SKILL.md" else directory / name
                    return _parse_skill(name, content, skill_dir=skill_dir)

        raise SkillLoadError(
            f"Skill '{name}' nicht gefunden in:\n"
            f"  {self._user_dir}/{name}.md\n"
            f"  {self._user_dir}/{name}/SKILL.md\n"
            f"  {self._builtin_dir}/{name}.md\n"
            f"  {self._builtin_dir}/{name}/SKILL.md"
        )

    def load_all(self) -> list[Skill]:
        """
        Lädt alle verfügbaren Skills aus beiden Verzeichnissen.
        Überspringe fehlerhafte Dateien (kein Crash).

        Returns:
            Liste aller gültigen Skills.
        """
        cache_key = (str(self._user_dir.resolve()), str(self._builtin_dir.resolve()))
        now = time.monotonic()
        cached = _SKILL_LIST_CACHE.get(cache_key)
        if cached and now - cached[0] < SKILL_CACHE_TTL_SECONDS:
            return cached[1]

        skills: list[Skill] = []
        seen_names: set[str] = set()

        for directory in [self._user_dir, self._builtin_dir]:
            if not directory.exists():
                continue
            candidates = [(md_file.stem, md_file, directory / md_file.stem) for md_file in sorted(directory.glob("*.md"))]
            candidates.extend(
                (skill_dir.name, skill_dir / "SKILL.md", skill_dir)
                for skill_dir in sorted(p for p in directory.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
            )
            for name, skill_file, skill_dir in candidates:
                if name in seen_names:
                    continue  # Nutzer-Skill hat Vorrang, nicht nochmal laden
                try:
                    skill = _parse_skill(name, skill_file.read_text(encoding="utf-8"), skill_dir=skill_dir)
                    skills.append(skill)
                    seen_names.add(name)
                except SkillLoadError:
                    continue  # Fehlerhafte Datei überspringen

        _SKILL_LIST_CACHE[cache_key] = (now, skills)
        return skills

    def resolve_trigger(self, trigger: str) -> Skill | None:
        """
        Findet einen Skill anhand seines Triggers.

        Returns:
            Skill-Objekt oder None wenn kein Trigger passt.
        """
        for skill in self.load_all():
            if skill.trigger == trigger:
                return skill
        return None

    def resolve_for_message(self, message: str) -> Skill | None:
        """Best-effort automatic skill resolver using positive and negative trigger metadata."""
        text = (message or "").lower()
        best: tuple[int, Skill] | None = None
        for skill in self.load_all():
            negative_text = " ".join(skill.when_not_to_use).lower()
            if negative_text and _phrase_score(text, negative_text) >= 2:
                continue
            haystack = " ".join([skill.description, *skill.when_to_use, skill.trigger]).lower()
            score = _phrase_score(text, haystack)
            if score > 0 and (best is None or score > best[0]):
                best = (score, skill)
        return best[1] if best else None

    def is_builtin(self, name: str) -> bool:
        """Gibt True zurück wenn der Skill ein Built-in ist (nicht löschbar)."""
        return (self._builtin_dir / f"{name}.md").exists() or (self._builtin_dir / name / "SKILL.md").exists()

    def is_user_skill(self, name: str) -> bool:
        """Gibt True zurück wenn ein Nutzer-Skill mit diesem Namen existiert."""
        return (self._user_dir / f"{name}.md").exists() or (self._user_dir / name / "SKILL.md").exists()

    def save(
        self,
        name: str,
        trigger: str,
        description: str,
        tools: list[str],
        system_prompt: str,
    ) -> Skill:
        """
        Speichert einen Nutzer-Skill als Markdown-Datei.

        Erstellt das Nutzer-Skills-Verzeichnis falls nicht vorhanden.
        Überschreibt vorhandene Dateien (für Update).

        Sicherheit:
          - Path-Traversal-Schutz (target muss in _user_dir liegen)
          - Dateiname wird auf Basisnamen reduziert

        Returns:
            Das gespeicherte Skill-Objekt (geparst zur Validierung).

        Raises:
            SkillLoadError:   wenn der resultierende Skill ungültig wäre
            PermissionError:  bei Path-Traversal-Versuch
        """
        self._user_dir.mkdir(parents=True, exist_ok=True)

        # Path-Traversal-Schutz: nur Basisname, kein ../
        safe_name = Path(name).name
        if not safe_name or safe_name.startswith("."):
            raise SkillLoadError(f"Ungültiger Skill-Name: '{name}'")

        path = (self._user_dir / f"{safe_name}.md").resolve()
        allowed = self._user_dir.resolve()
        if not str(path).startswith(str(allowed)):
            raise PermissionError(
                f"Sicherheitsverletzung: Pfad '{path}' liegt außerhalb "
                f"des erlaubten Verzeichnisses '{allowed}'."
            )

        tools_str = ", ".join(tools) if tools else ""
        content = (
            f"# {safe_name}\n\n"
            f"**Trigger**: {trigger}\n"
            f"**Description**: {description}\n"
            f"**Tools**: {tools_str}\n\n"
            f"## System Prompt\n\n"
            f"{system_prompt}\n"
        )

        # Validate before writing
        _parse_skill(safe_name, content)  # raises SkillLoadError if invalid

        path.write_text(content, encoding="utf-8")
        self._clear_cache()
        return _parse_skill(safe_name, content)

    def delete(self, name: str) -> None:
        """
        Löscht einen Nutzer-Skill.

        Raises:
            SkillLoadError: wenn Skill nicht als Nutzer-Skill existiert
            PermissionError: wenn Skill ein Built-in ist
        """
        if self.is_builtin(name):
            raise PermissionError(
                f"Built-in Skill '{name}' kann nicht gelöscht werden."
            )
        path = self._user_dir / f"{name}.md"
        if not path.exists():
            raise SkillLoadError(f"Nutzer-Skill '{name}' nicht gefunden.")
        path.unlink()
        self._clear_cache()

    def _clear_cache(self) -> None:
        _SKILL_LIST_CACHE.pop((str(self._user_dir.resolve()), str(self._builtin_dir.resolve())), None)

    async def run_test(self, name: str) -> SkillTestResult:
        """
        Führt den Selbst-Test eines Skills durch.

        Nutzt chat_with_tools mit dem Skill als System-Prompt.
        Prüft ob das erwartete Tool aufgerufen wurde.

        Returns:
            SkillTestResult (passed = True/False)
        """
        from core.chat import chat_with_tools, OllamaNotReachableError
        from core.tools import get_tool_schemas

        # Skill laden
        try:
            skill = self.load(name)
        except SkillLoadError as exc:
            return SkillTestResult(
                skill_name=name,
                passed=False,
                message=f"Skill konnte nicht geladen werden: {exc}",
            )

        if not skill.test.input:
            return SkillTestResult(
                skill_name=name,
                passed=True,
                message="Kein Test definiert (übersprungen).",
            )

        # Ollama-Aufruf mit Skill-System-Prompt
        tool_called: list[str] = []
        chunks: list[str] = []

        history = [
            {"role": "system", "content": skill.system_prompt},
            {"role": "user",   "content": skill.test.input},
        ]

        try:
            import os
            model = os.environ.get("MIMI_NOX_MODEL", "gemma4:12b")
            response = await chat_with_tools(
                model=model,
                history=history,
                on_chunk=chunks.append,
                on_tool_start=lambda n, _: tool_called.append(n),
            )
        except OllamaNotReachableError:
            return SkillTestResult(
                skill_name=name,
                passed=False,
                message="Ollama nicht erreichbar – Test übersprungen.",
            )
        except Exception as exc:
            return SkillTestResult(
                skill_name=name,
                passed=False,
                message=f"Fehler während Test: {exc}",
            )

        full_response = response or "".join(chunks)

        # Prüfungen
        if skill.test.expect_tool and skill.test.expect_tool not in tool_called:
            return SkillTestResult(
                skill_name=name,
                passed=False,
                message=(
                    f"Erwartet Tool '{skill.test.expect_tool}' aber aufgerufen: "
                    f"{tool_called or 'keines'}"
                ),
                tool_called=", ".join(tool_called),
                response=full_response[:200],
            )

        if skill.test.expect_contains:
            if skill.test.expect_contains.lower() not in full_response.lower():
                return SkillTestResult(
                    skill_name=name,
                    passed=False,
                    message=(
                        f"Antwort enthält nicht '{skill.test.expect_contains}'"
                    ),
                    tool_called=", ".join(tool_called),
                    response=full_response[:200],
                )

        return SkillTestResult(
            skill_name=name,
            passed=True,
            message="Test bestanden.",
            tool_called=", ".join(tool_called),
            response=full_response[:200],
        )
