from pathlib import Path


EXPECTED_BUILTIN_TRIGGERS = {
    "/chart",
    "/deck",
    "/review",
    "/files",
    "/help",
    "/notebook",
    "/pdf",
    "/shell",
    "/svg",
    "/scan",
    "/project",
    "/research",
    "/write",
}


def test_given_builtin_skills_when_loaded_then_public_trigger_set_is_complete():
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader

    skills = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR).load_all()
    triggers = {skill.trigger for skill in skills}

    assert triggers == EXPECTED_BUILTIN_TRIGGERS
    assert len(triggers) == len(skills)


def test_given_builtin_skills_when_tools_declared_then_every_tool_exists():
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader
    from core.tools import TOOL_MAP

    skills = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR).load_all()
    missing = {
        skill.name: [tool for tool in skill.tools if tool not in TOOL_MAP]
        for skill in skills
    }
    missing = {name: tools for name, tools in missing.items() if tools}

    assert missing == {}


def test_given_high_impact_builtin_skills_when_loaded_then_they_require_real_tool_outputs():
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader

    loader = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR)

    for name, tool_name in {
        "chart-creator": "generate_chart",
        "deck-creator": "create_pptx_deck",
        "pdf-creator": "create_pdf",
        "svg-creator": "create_svg",
        "web-researcher": "web_search",
        "shell-helper": "run_shell",
        "vision-assistant": "analyze_image",
        "project-assistant": "analyze_project",
        "source-notebook": "create_source_notebook",
    }.items():
        skill = loader.load(name)
        assert tool_name in skill.tools
        assert "IMMER" in skill.system_prompt or "Always" in skill.system_prompt or "Nutze" in skill.system_prompt


def test_given_builtin_skills_when_loaded_then_each_has_high_end_output_contract():
    """
    GIVEN MiMi Nox ships public built-in skills
    WHEN their prompts are loaded
    THEN every skill defines a premium output contract and quality gate.
    """
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader

    skills = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR).load_all()
    missing = {
        skill.name: [
            marker
            for marker in ["Output Contract", "Quality Gate", "Do not simulate"]
            if marker not in skill.system_prompt
        ]
        for skill in skills
    }
    missing = {name: markers for name, markers in missing.items() if markers}

    assert missing == {}


def test_given_tool_using_builtin_skills_when_loaded_then_they_require_evidence_from_real_tools():
    """
    GIVEN a built-in skill declares tools
    WHEN the prompt is inspected
    THEN it must require evidence from real tool output instead of invented results.
    """
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader

    skills = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR).load_all()
    missing = [
        skill.name
        for skill in skills
        if skill.tools and "real tool output" not in skill.system_prompt
    ]

    assert missing == []


def test_given_pdf_skill_when_loaded_then_it_requires_report_grade_documents():
    """
    GIVEN the PDF skill is a flagship user-facing artifact generator
    WHEN the prompt and tool schema are inspected
    THEN they require report-grade structure and verification-ready output.
    """
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader
    from core.tools import get_tool_schemas

    skill = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR).load("pdf-creator")
    prompt = skill.system_prompt
    assert "Executive Summary" in prompt
    assert "source notes" in prompt
    assert "appendix" in prompt
    assert "artifact-grade" in prompt

    schemas = get_tool_schemas()
    create_pdf_schema = next(s["function"] for s in schemas if s["function"]["name"] == "create_pdf")
    description = create_pdf_schema["description"]
    assert "Executive Summary" in description
    assert "quality-checked" in description


def test_given_high_impact_builtin_skills_when_loaded_then_they_have_progressive_references():
    """
    GIVEN high-impact skills should stay concise while offering deeper guidance
    WHEN they are loaded
    THEN each has external rubric/example support available to the quality layer.
    """
    from core.skills import BUILTIN_SKILLS_DIR, SkillLoader

    loader = SkillLoader(skills_dir=Path("/tmp/mimi-nox-no-user-skills"), builtin_dir=BUILTIN_SKILLS_DIR)
    for name in ["pdf-creator", "deck-creator", "project-assistant", "vision-assistant", "code-reviewer", "file-assistant"]:
        skill = loader.load(name)
        assert skill.has_references is True
        assert "Quality Rubric" in skill.reference_text
        assert "Golden Example" in skill.example_text
