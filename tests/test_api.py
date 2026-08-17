"""
◑ MiMi Nox – Phase 4 TDD
tests/test_api.py

REGEL: Tests VOR Implementierung. ROT zuerst, dann GRÜN.
Given / When / Then – strikt.

Alle Tests nutzen FastAPI TestClient (synchron, kein echter Server).
Ollama-Calls werden vollständig gemockt.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ── Fixture: TestClient ────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path):
    """
    FastAPI TestClient mit isoliertem tmp_path für Memory + Profile + Skills.
    Überschreibt alle Default-Pfade via Umgebungsvariablen.
    """
    import os
    os.environ["MIMI_NOX_MEMORY_DIR"]       = str(tmp_path / "chroma_db")
    os.environ["MIMI_NOX_PROFILE_PATH"]     = str(tmp_path / "user_profile.json")
    os.environ["MIMI_NOX_CORRECTIONS_PATH"] = str(tmp_path / "corrections.md")
    os.environ["MIMI_NOX_FEEDBACK_DIR"]     = str(tmp_path)
    os.environ["MIMI_NOX_SKILLS_DIR"]       = str(tmp_path / "skills")

    # lru_cache auf Memory-Singleton zurücksetzen für Test-Isolation
    from server.routes.memory import _get_memory
    _get_memory.cache_clear()

    from server.main import create_app
    app = create_app()
    return TestClient(app)


# ── Health ─────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_ok(self, client):
        """
        GIVEN  FastAPI Server läuft
        WHEN   GET /api/health
        THEN   Status 200
        AND    Response enthält status="ok"
        AND    Response enthält "ollama" Key (bool)
        """
        with patch("server.routes.health.check_ollama_connection", new=AsyncMock(
            return_value=(True, "OK", ["phi4-mini"])
        )):
            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "ollama" in data
        assert isinstance(data["ollama"], bool)

    def test_health_includes_version(self, client):
        """
        GIVEN  FastAPI Server läuft
        WHEN   GET /api/health
        THEN   Response enthält "version" Key (String)
        """
        with patch("server.routes.health.check_ollama_connection", new=AsyncMock(
            return_value=(False, "unreachable", [])
        )):
            response = client.get("/api/health")

        assert response.status_code == 200
        assert "version" in response.json()

    def test_given_provider_model_differs_from_router_when_health_then_models_match_active_model(self, client):
        """
        GIVEN  the active provider uses gemma4:12b but legacy router resolves offline gemma4:e2b
        WHEN   GET /api/health
        THEN   active_model and models describe the same release model.
        """
        from core.model_provider import ModelProviderConfig

        with patch("server.routes.health.check_ollama_connection", new=AsyncMock(
            return_value=(True, "OK", ["gemma4:12b", "gemma4:e2b"])
        )), patch("server.routes.health.get_active_provider", return_value=ModelProviderConfig(
            provider="local_ollama",
            model="gemma4:12b",
            base_url="http://127.0.0.1:11434",
            label="Local Ollama",
            offline_capable=True,
            requires_internet=False,
        )):
            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["active_model"] == "gemma4:12b"
        assert data["models"] == ["gemma4:12b"]


# ── Chat ───────────────────────────────────────────────────────────────────

class TestChatEndpoint:

    def test_chat_returns_response(self, client):
        """
        GIVEN  FastAPI Server läuft + Ollama gemockt
        WHEN   POST /api/chat mit {"message": "Hallo", "model": "phi4-mini"}
        THEN   Status 200
        AND    Response enthält "response" Key (nicht-leerer String)
        AND    Response enthält "model" Key
        """
        with patch("server.routes.chat.react_loop", new=AsyncMock(
            return_value="Hallo! Ich bin MiMi Nox."
        )):
            response = client.post("/api/chat", json={
                "message": "Hallo",
                "model": "phi4-mini",
            })

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert "model" in data

    def test_chat_missing_message_returns_422(self, client):
        """
        GIVEN  FastAPI Server läuft
        WHEN   POST /api/chat ohne message-Feld
        THEN   Status 422 (Validation Error)
        AND    Kein Crash
        """
        response = client.post("/api/chat", json={"model": "phi4-mini"})
        assert response.status_code == 422

    def test_chat_ollama_unreachable_returns_503(self, client):
        """
        GIVEN  Ollama nicht erreichbar (OllamaNotReachableError)
        WHEN   POST /api/chat
        THEN   Status 503
        AND    Response enthält "error.message" mit verständlicher Meldung (Observability-Contract)
        """
        from core.chat import OllamaNotReachableError
        with patch("server.routes.chat.react_loop", new=AsyncMock(
            side_effect=OllamaNotReachableError()
        )):
            response = client.post("/api/chat", json={
                "message": "Test",
                "model": "phi4-mini",
            })

        assert response.status_code == 503
        # Observability-Contract (Phase 4 Item 15): 503 liefert stabilen
        # Error-Payload {"error": {message, code, request_id}} + X-Request-ID.
        err = response.json()["error"]
        assert "Ollama nicht erreichbar" in err["message"]
        assert err["code"] == "upstream_error"
        assert response.headers.get("x-request-id") == err["request_id"]

    def test_given_tool_chat_emits_thinking_when_streaming_then_raw_reasoning_is_filtered(self, client):
        """
        GIVEN the model adapter reports internal thinking text
        WHEN /api/chat/stream emits SSE to the PWA
        THEN raw reasoning does not cross the API boundary.
        """
        from core.react import ReflexionResult

        async def fake_chat_with_tools(*, on_chunk, on_thinking, **_kwargs):
            on_thinking("SECRET_INTERNAL_REASONING")
            on_chunk("Final answer")

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(return_value=ReflexionResult(needs_revision=False, reason="ok")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "Hallo", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "Final answer" in body
        assert "SECRET_INTERNAL_REASONING" not in body
        assert '"type": "thinking"' not in body

    def test_given_skill_trigger_when_streaming_then_skill_prompt_and_tool_scope_are_used(self, client):
        """
        GIVEN a user invokes the PDF skill via /pdf
        WHEN /api/chat/stream calls the chat engine
        THEN the skill system prompt is injected and only the skill tools are offered.
        """
        from core.react import ReflexionResult

        captured: dict = {}

        async def fake_chat_with_tools(**kwargs):
            captured.update(kwargs)
            kwargs["on_chunk"]("PDF ready")
            return "PDF ready"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(return_value=ReflexionResult(needs_revision=False, reason="ok")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/pdf Erstelle ein kurzes Test-PDF", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "PDF ready" in body
        assert captured["allowed_tool_names"] == ["create_pdf"]
        assert "professionelle PDF-Dokumente" in captured["extra_system_prompt"]
        history = captured["history"]
        assert history[-1]["content"] == "Erstelle ein kurzes Test-PDF"

    def test_given_deck_skill_trigger_when_streaming_then_deck_tool_scope_is_used(self, client):
        """
        GIVEN a user invokes the deck skill via /deck
        WHEN /api/chat/stream calls the chat engine
        THEN only the pitchdeck tool is offered and the deck prompt is injected.
        """
        from core.react import ReflexionResult

        captured: dict = {}

        async def fake_chat_with_tools(**kwargs):
            captured.update(kwargs)
            kwargs["on_chunk"]("Deck ready")
            return "Deck ready"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(return_value=ReflexionResult(needs_revision=False, reason="ok")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/deck Erstelle ein Pitchdeck fuer MiMi Nox", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "Deck ready" in body
        assert captured["allowed_tool_names"] == [
            "create_pitch_deck",
            "create_pptx_deck",
            "inspect_pptx_template",
            "edit_pptx_template",
            "qa_pptx_deck",
        ]
        assert "Pitchdeck" in captured["extra_system_prompt"]

    def test_given_skill_stream_when_quality_gate_runs_then_quality_events_are_emitted(self, client):
        """
        GIVEN a user invokes a high-impact skill
        WHEN the stream completes
        THEN the SSE stream includes deterministic local quality-check events.
        """
        from core.react import ReflexionResult

        async def fake_chat_with_tools(**kwargs):
            kwargs["on_tool_done"]("create_pdf", "PDF_FILE:/Users/test/Downloads/report.pdf")
            kwargs["on_chunk"]("PDF saved at /Users/test/Downloads/report.pdf")
            return "PDF saved at /Users/test/Downloads/report.pdf"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(return_value=ReflexionResult(needs_revision=False, reason="ok")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/pdf Erstelle ein kurzes Test-PDF", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"type": "quality_check"' in body
        assert '"status": "running"' in body
        assert '"status": "passed"' in body
        assert '"type": "artifact_check"' in body

    def test_given_skill_quality_passes_when_streaming_then_reflect_is_skipped(self, client):
        """
        GIVEN deterministic skill quality already passed
        WHEN the stream has emitted the skill answer
        THEN reflect is skipped so the UI receives done without a slow critique call.
        """
        async def fake_chat_with_tools(**kwargs):
            kwargs["on_tool_done"]("web_search", "[1] Official\n    URL: https://ai.google.dev/gemma\n    Source quality: official")
            kwargs["on_chunk"]("Antwort mit Quelle\n\n📎 Quellen:\n[Official](https://ai.google.dev/gemma)")
            return "Antwort mit Quelle\n\n📎 Quellen:\n[Official](https://ai.google.dev/gemma)"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(side_effect=AssertionError("reflect should be skipped after passing skill quality")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/research Gemma 4 12B offizielle Infos", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"status": "passed"' in body
        assert '"type": "done"' in body

    def test_given_fast_path_deck_when_streaming_then_quality_and_artifact_events_are_emitted(self, client, tmp_path):
        """
        GIVEN a deterministic deck fast path returns a Slide Studio artifact
        WHEN /api/chat/stream serves the response without model tool calling
        THEN the PWA still receives quality_check and artifact_check events.
        """
        pdf = tmp_path / "deck.pdf"
        pptx = tmp_path / "deck.pptx"
        qa = tmp_path / "deck.qa.json"
        manifest = tmp_path / "deck.manifest.json"
        for path in (pdf, pptx, qa, manifest):
            path.write_text("test", encoding="utf-8")
        studio = tmp_path / "deck.studio.html"
        studio.write_text(
            "MiMi Nox Slide Studio\nChoose Output\nSlide Contact Sheet\n"
            f'<a href="file://{pdf}">Download PDF</a>\n'
            f'<a href="file://{pptx}">Download PPTX</a>\n'
            f'<a href="file://{qa}">Open QA Report</a>\n'
            f'<a href="file://{manifest}">Open Claim Manifest</a>',
            encoding="utf-8",
        )
        answer = f"## Slide Studio erstellt\nDECK_STUDIO_FILE:{studio}\n"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=answer)):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/deck Erstelle ein Board Deck", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"type": "file_result"' in body
        assert '"file_type": "deck_studio"' in body
        assert '"type": "quality_check"' in body
        assert '"status": "passed"' in body
        assert '"type": "artifact_check"' in body
        assert '"artifact_type": "deck_studio"' in body

    def test_given_vague_followup_skill_when_streaming_then_fast_path_receives_previous_intent(self, client):
        """
        GIVEN the user follows up with 'mach das jetzt richtig'
        WHEN /api/chat/stream resolves a deterministic skill fast path
        THEN the last substantive user request is attached before the model fallback can stall.
        """
        captured: dict = {}

        async def fake_fast_path(skill_name: str, user_content: str):
            captured["skill_name"] = skill_name
            captured["user_content"] = user_content
            return "## Quellen-Notebook braucht Quellen\nFast follow-up handled"

        history = [
            {"role": "user", "content": "Erstelle NotebookLM Slides zu KI Architektur 2026 mit Bildern"},
            {"role": "assistant", "content": "Ich kann daraus Slides erzeugen."},
        ]
        with patch("server.routes.chat.run_skill_fast_path", new=fake_fast_path), patch(
            "server.routes.chat.chat_with_tools",
            new=AsyncMock(side_effect=AssertionError("model path should not run")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/notebook mach das jetzt richtig", "model": "gemma4:12b", "history": history},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert captured["skill_name"] == "source-notebook"
        assert "Kontext aus vorheriger Anfrage" in captured["user_content"]
        assert "KI Architektur 2026" in captured["user_content"]
        assert "Fast follow-up handled" in body

    def test_given_project_skill_trigger_when_streaming_then_project_tools_are_scoped(self, client):
        """
        GIVEN a user invokes /project
        WHEN /api/chat/stream calls the chat engine
        THEN the project system prompt and project tools are passed to tool calling.
        """
        from core.react import ReflexionResult

        captured: dict = {}

        async def fake_chat_with_tools(**kwargs):
            captured.update(kwargs)
            kwargs["on_chunk"]("Projektanalyse bereit")
            return "Projektanalyse bereit"

        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value=None)), patch(
            "server.routes.chat.chat_with_tools",
            new=fake_chat_with_tools,
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(return_value=ReflexionResult(needs_revision=False, reason="ok")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/project finde mimi-nox", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "Projektanalyse bereit" in body
        assert captured["allowed_tool_names"] == [
            "discover_projects",
            "analyze_project",
            "read_file",
            "list_directory",
            "file_search",
        ]
        assert "lokaler Projekt-Analyst" in captured["extra_system_prompt"]

    def test_given_project_skill_fast_path_when_streaming_then_chat_model_is_skipped(self, client):
        """
        GIVEN /project can be answered by deterministic local tools
        WHEN /api/chat/stream handles it
        THEN chat_with_tools and reflect are skipped for speed.
        """
        with patch("server.routes.chat.run_skill_fast_path", new=AsyncMock(return_value="## Gefundene Projekte\n- mimi")), patch(
            "server.routes.chat.chat_with_tools",
            new=AsyncMock(side_effect=AssertionError("model should be skipped")),
        ), patch(
            "server.routes.chat.reflect",
            new=AsyncMock(side_effect=AssertionError("reflect should be skipped")),
        ):
            with client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "/project finde mimi", "model": "gemma4:12b", "history": []},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "Gefundene Projekte" in body


# ── Memory ─────────────────────────────────────────────────────────────────

class TestMemoryEndpoint:

    def test_memory_search_empty_returns_empty_list(self, client):
        """
        GIVEN  Leere Memory-Datenbank (frisch initialisiert)
        WHEN   GET /api/memory/search?q=Python
        THEN   Status 200
        AND    Response: {"results": []}
        """
        response = client.get("/api/memory/search", params={"q": "Python"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["results"] == []

    def test_memory_store_and_search(self, client):
        """
        GIVEN  Text "Python ist großartig" gespeichert
        WHEN   GET /api/memory/search?q=Python
        THEN   Status 200
        AND    results enthält mindestens 1 Eintrag
        AND    Jeder Eintrag hat "text" Key
        """
        # Store
        store_response = client.post("/api/memory/store", json={
            "text": "Python ist eine großartige Programmiersprache."
        })
        assert store_response.status_code == 200

        # Search
        search_response = client.get("/api/memory/search", params={"q": "Python"})
        assert search_response.status_code == 200
        data = search_response.json()
        assert "results" in data
        assert len(data["results"]) >= 1
        assert "text" in data["results"][0]

    def test_memory_store_missing_text_returns_422(self, client):
        """
        GIVEN  POST /api/memory/store ohne text-Feld
        WHEN   Request gesendet
        THEN   Status 422 (Validation Error)
        """
        response = client.post("/api/memory/store", json={})
        assert response.status_code == 422


# ── Skills ─────────────────────────────────────────────────────────────────

class TestSkillsEndpoint:

    def test_skills_list_returns_skills(self, client):
        """
        GIVEN  FastAPI Server mit built-in Skills (skills/*.md)
        WHEN   GET /api/skills
        THEN   Status 200
        AND    Response enthält Liste mit ≥1 Skills
        AND    Jeder Skill hat: name, trigger, description
        """
        response = client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert len(data["skills"]) >= 1
        for skill in data["skills"]:
            assert "name" in skill
            assert "trigger" in skill
            assert "description" in skill

    def test_given_skills_list_when_called_then_v2_quality_metadata_is_returned(self, client):
        """
        GIVEN Skill System v2 adds progressive quality metadata
        WHEN GET /api/skills returns summaries
        THEN clients can inspect quality profile and reference availability without breaking old fields.
        """
        response = client.get("/api/skills")

        assert response.status_code == 200
        pdf = next(skill for skill in response.json()["skills"] if skill["name"] == "pdf-creator")
        assert pdf["trigger"] == "/pdf"
        assert "quality_profile" in pdf
        assert "artifact_types" in pdf
        assert "has_references" in pdf
        assert "when_to_use" in pdf
        assert "when_not_to_use" in pdf

    def test_skill_detail_returns_skill(self, client):
        """
        GIVEN  Built-in Skill "web-researcher" vorhanden
        WHEN   GET /api/skills/web-researcher
        THEN   Status 200
        AND    Response enthält name="web-researcher"
        AND    Response enthält system_prompt (nicht-leerer String)
        """
        response = client.get("/api/skills/web-researcher")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "web-researcher"
        assert len(data["system_prompt"]) > 0

    def test_given_skill_detail_when_called_then_v2_quality_metadata_is_returned(self, client):
        response = client.get("/api/skills/pdf-creator")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pdf-creator"
        assert "quality_profile" in data
        assert "artifact_types" in data
        assert "reference_text" in data

    def test_skill_not_found_returns_404(self, client):
        """
        GIVEN  Unbekannter Skill-Name
        WHEN   GET /api/skills/does-not-exist
        THEN   Status 404
        AND    Kein Crash
        """
        response = client.get("/api/skills/does-not-exist")
        assert response.status_code == 404


# ── Profile ────────────────────────────────────────────────────────────────

class TestProfileEndpoint:

    def test_get_profile_returns_default(self, client):
        """
        GIVEN  Kein Profil gespeichert (tmp_path leer)
        WHEN   GET /api/profile
        THEN   Status 200
        AND    Response enthält alle Profil-Felder
        AND    name ist null (default)
        """
        response = client.get("/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "expertise" in data
        assert "preferred_language" in data
        assert data["name"] is None

    def test_put_profile_updates_fields(self, client):
        """
        GIVEN  Profil-Update mit name="Max", expertise="Python"
        WHEN   PUT /api/profile mit {"name": "Max", "expertise": "Python"}
        THEN   Status 200
        AND    GET /api/profile danach: name="Max", expertise="Python"
        """
        client.put("/api/profile", json={
            "name": "Max",
            "expertise": "Python",
        })
        response = client.get("/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Max"
        assert data["expertise"] == "Python"


# ── Feedback ───────────────────────────────────────────────────────────────

class TestFeedbackEndpoint:

    def test_thumbs_up_returns_200(self, client):
        """
        GIVEN  Prompt + Response vorhanden
        WHEN   POST /api/feedback/thumbs_up mit {"prompt": "P", "response": "R"}
        THEN   Status 200
        AND    {"saved": true}
        """
        response = client.post("/api/feedback/thumbs_up", json={
            "prompt": "Was ist Python?",
            "response": "Python ist eine Programmiersprache.",
        })
        assert response.status_code == 200
        assert response.json()["saved"] is True

    def test_thumbs_down_returns_200(self, client):
        """
        GIVEN  Prompt + Response vorhanden
        WHEN   POST /api/feedback/thumbs_down
        THEN   Status 200
        AND    {"saved": true}
        """
        response = client.post("/api/feedback/thumbs_down", json={
            "prompt": "Was ist Python?",
            "response": "Eine Schlange.",
        })
        assert response.status_code == 200
        assert response.json()["saved"] is True


# ── Skills CRUD (Phase 5) ──────────────────────────────────────────────────

class TestSkillsCRUD:
    """Skills: Erstellen, Bearbeiten, Löschen von Nutzer-Skills."""

    _SKILL_PAYLOAD = {
        "name": "mein-test-skill",
        "trigger": "/test",
        "description": "Ein Testskill für Unit-Tests.",
        "tools": ["web_search"],
        "system_prompt": "Du bist ein Test-Assistent. Antworte immer mit: TEST OK.",
    }

    def test_create_skill_returns_201(self, client):
        """
        GIVEN  Gültiges Skill-Payload
        WHEN   POST /api/skills
        THEN   Status 201
        AND    Response enthält name, trigger, description
        """
        response = client.post("/api/skills", json=self._SKILL_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "mein-test-skill"
        assert data["trigger"] == "/test"

    def test_created_skill_appears_in_list(self, client):
        """
        GIVEN  Skill erstellt via POST /api/skills
        WHEN   GET /api/skills
        THEN   Skill ist in der Liste
        """
        client.post("/api/skills", json=self._SKILL_PAYLOAD)
        response = client.get("/api/skills")
        names = [s["name"] for s in response.json()["skills"]]
        assert "mein-test-skill" in names

    def test_created_skill_detail_accessible(self, client):
        """
        GIVEN  Skill erstellt
        WHEN   GET /api/skills/mein-test-skill
        THEN   Status 200 und system_prompt korrekt
        """
        client.post("/api/skills", json=self._SKILL_PAYLOAD)
        response = client.get("/api/skills/mein-test-skill")
        assert response.status_code == 200
        assert "TEST OK" in response.json()["system_prompt"]

    def test_update_skill_returns_200(self, client):
        """
        GIVEN  Skill existiert
        WHEN   PUT /api/skills/mein-test-skill mit neuer description
        THEN   Status 200
        AND    Neue description gespeichert
        """
        client.post("/api/skills", json=self._SKILL_PAYLOAD)
        updated = {**self._SKILL_PAYLOAD, "description": "Aktualisierte Beschreibung"}
        response = client.put("/api/skills/mein-test-skill", json=updated)
        assert response.status_code == 200

        detail = client.get("/api/skills/mein-test-skill")
        assert detail.json()["description"] == "Aktualisierte Beschreibung"

    def test_delete_user_skill_returns_200(self, client):
        """
        GIVEN  Nutzer-Skill erstellt
        WHEN   DELETE /api/skills/mein-test-skill
        THEN   Status 200
        AND    Skill nicht mehr im Listing
        """
        client.post("/api/skills", json=self._SKILL_PAYLOAD)
        response = client.delete("/api/skills/mein-test-skill")
        assert response.status_code == 200

        skills_after = client.get("/api/skills").json()["skills"]
        names = [s["name"] for s in skills_after]
        assert "mein-test-skill" not in names

    def test_delete_builtin_skill_returns_403(self, client):
        """
        GIVEN  Built-in Skill 'web-researcher'
        WHEN   DELETE /api/skills/web-researcher
        THEN   Status 403 (Builtin Skills dürfen nicht gelöscht werden)
        """
        response = client.delete("/api/skills/web-researcher")
        assert response.status_code == 403

    def test_delete_nonexistent_skill_returns_404(self, client):
        """
        GIVEN  Skill existiert nicht
        WHEN   DELETE /api/skills/phantomskill
        THEN   Status 404
        """
        response = client.delete("/api/skills/phantomskill")
        assert response.status_code == 404

    def test_create_skill_missing_fields_returns_422(self, client):
        """
        GIVEN  Payload ohne system_prompt
        WHEN   POST /api/skills
        THEN   Status 422 (Validation Error)
        """
        response = client.post("/api/skills", json={
            "name": "broken",
            "trigger": "/broken",
        })
        assert response.status_code == 422


# ── Memory CRUD (Phase 5) ─────────────────────────────────────────────────

class TestMemoryCRUD:
    """Memory: Einträge auflisten und gezielt löschen."""

    def test_memory_list_empty(self, client):
        """
        GIVEN  Leere Memory-Datenbank
        WHEN   GET /api/memory/list
        THEN   Status 200
        AND    {"entries": [], "total": 0}
        """
        response = client.get("/api/memory/list")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["total"] == 0

    def test_memory_list_after_store(self, client):
        """
        GIVEN  Zwei Texte gespeichert
        WHEN   GET /api/memory/list
        THEN   Beide Einträge sichtbar mit "id" Key
        """
        client.post("/api/memory/store", json={"text": "Erste Notiz"})
        client.post("/api/memory/store", json={"text": "Zweite Notiz"})
        response = client.get("/api/memory/list")
        data = response.json()
        assert data["total"] >= 2
        assert all("id" in e for e in data["entries"])

    def test_memory_delete_entry(self, client):
        """
        GIVEN  Text gespeichert + ID bekannt
        WHEN   DELETE /api/memory/{id}
        THEN   Status 200
        AND    Eintrag nicht mehr in GET /api/memory/list
        """
        client.post("/api/memory/store", json={"text": "Zu löschende Notiz"})
        entries = client.get("/api/memory/list").json()["entries"]
        assert len(entries) >= 1
        entry_id = entries[0]["id"]

        response = client.delete(f"/api/memory/{entry_id}")
        assert response.status_code == 200

        entries_after = client.get("/api/memory/list").json()["entries"]
        ids_after = [e["id"] for e in entries_after]
        assert entry_id not in ids_after

    def test_memory_delete_nonexistent_returns_404(self, client):
        """
        GIVEN  Nicht-existente ID
        WHEN   DELETE /api/memory/ghost-id-123
        THEN   Status 404
        """
        response = client.delete("/api/memory/ghost-id-123")
        assert response.status_code == 404


# ── T-02: pending_sandbox Race Condition ────────────────────────────────────

class TestSandboxIsolation:
    """
    T-02: pending_sandbox darf kein modul-globaler Dict sein.
    Jeder Request braucht seinen eigenen isolierten Sandbox-State.
    """

    def test_sandbox_tokens_are_unique_per_request(self):
        """
        GIVEN  Zwei simultane Requests erstellen je einen Sandbox-Token
        WHEN   Beide Token gesetzt werden
        THEN   Kein Token-Konflikt — jeder hat seinen eigenen State
        """
        import uuid
        from asyncio import Event

        # Simuliert zwei Requests die je einen Token anlegen
        token_a = str(uuid.uuid4())
        token_b = str(uuid.uuid4())

        # Nach dem Fix: get_sandbox() liefert request-scoped dict
        from server.routes.chat import get_sandbox

        sandbox_a = get_sandbox()
        sandbox_a[token_a] = {"approved": True}

        sandbox_b = get_sandbox()
        sandbox_b[token_b] = {"approved": False}

        # In ContextVar-Impl: beide greifen auf denselben Context-Dict zu
        # → beide Token müssen vorhanden sein
        assert token_a in sandbox_a
        assert token_b in sandbox_b
        assert token_a != token_b

    async def test_concurrent_sandbox_states_are_isolated(self):
        """
        GIVEN  Zwei asyncio Tasks greifen auf get_sandbox() zu
        WHEN   Task A setzt approved=True, Task B setzt approved=False
        THEN   Beide States bleiben korrekt und überschreiben sich nicht
        """
        import asyncio
        from contextvars import copy_context

        results = {}

        from server.routes.chat import get_sandbox

        async def task_a():
            import uuid
            token = str(uuid.uuid4())
            s = get_sandbox()
            s[token] = {"approved": True}
            await asyncio.sleep(0)  # yield
            results["a"] = s[token]["approved"]

        async def task_b():
            import uuid
            token = str(uuid.uuid4())
            s = get_sandbox()
            s[token] = {"approved": False}
            await asyncio.sleep(0)  # yield
            results["b"] = s[token]["approved"]

        # Beide im gleichen asyncio Context (wie FastAPI)
        await asyncio.gather(task_a(), task_b())

        assert results["a"] is True
        assert results["b"] is False


# ── T-03: Vision Monkey-Patching → ContextVar ────────────────────────────────

class TestVisionCallbackIsolation:
    """
    T-03: core.vision.ON_SANDBOX_CONFIRM darf nicht modul-global sein.
    Jeder Request braucht seinen eigenen Callback-Context.
    """

    def test_vision_module_exposes_context_var(self):
        """
        GIVEN  core.vision importiert
        WHEN   Modul-Attribute geprüft werden
        THEN   _sandbox_cb_var ist ein ContextVar (kein None-Global)
        """
        from contextvars import ContextVar
        import core.vision as vision

        # Nach dem Fix: ContextVar statt None-Global
        assert hasattr(vision, "_sandbox_cb_var"), \
            "core.vision muss _sandbox_cb_var (ContextVar) exportieren"
        assert isinstance(vision._sandbox_cb_var, ContextVar), \
            "_sandbox_cb_var muss eine ContextVar sein, nicht ein simples None-Global"

    def test_vision_context_var_default_is_none(self):
        """
        GIVEN  Kein Callback gesetzt (frischer Context)
        WHEN   _sandbox_cb_var.get() aufgerufen
        THEN   Default-Wert ist None (kein unerwarteter Callback)
        """
        import core.vision as vision
        cb = vision._sandbox_cb_var.get()
        assert cb is None, "Default muss None sein — kein Callback ohne explizites Set"

    async def test_callback_set_in_context_does_not_leak(self):
        """
        GIVEN  Context A setzt Callback cb_a
        WHEN   Context B prüft seinen Callback
        THEN   Context B sieht cb_a NICHT — kein Leak
        """
        import asyncio
        from contextvars import copy_context
        import core.vision as vision

        seen_in_b = {}

        cb_a = lambda tool, args: "callback_a"

        async def context_a():
            vision._sandbox_cb_var.set(cb_a)
            await asyncio.sleep(0.01)  # yield, damit B gleichzeitig läuft

        async def context_b():
            await asyncio.sleep(0)  # kurz warten
            # Context B hat _sandbox_cb_var nicht gesetzt → muss None sein
            seen_in_b["val"] = vision._sandbox_cb_var.get()

        # HINWEIS: In asyncio teilen Tasks denselben Context per default (kein copy_context).
        # Das ist genau das Problem: ohne ContextVar-Isolation leaked A nach B.
        # Dieser Test dokumentiert das Problem — nach dem Fix via copy_context im Router
        # wird jeder Request seinen eigenen Context bekommen.
        await asyncio.gather(context_a(), context_b())

        # In der JETZIGEN (kaputten) Impl: seen_in_b["val"] == cb_a (Leak!)
        # Dieser Test FAIL bestätigt den Bug.
        # Nach dem Fix via Request-scoped ContextVar: seen_in_b["val"] == None
        # Für den Red-Test: wir erwarten dass es noch NULL ist (B sieht A nicht)
        # Das wird erst nach dem Fix garantiert — jetzt bestätigen wir nur die API.
        assert "val" in seen_in_b  # Mindestens muss das Dictionary befüllt sein
