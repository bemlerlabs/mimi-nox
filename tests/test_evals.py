from pathlib import Path


def test_given_skill_eval_fixtures_when_loaded_then_each_builtin_skill_has_five_cases():
    from scripts.eval_skills import load_eval_cases

    cases = load_eval_cases(Path("evals/skills"))
    by_skill: dict[str, list] = {}
    for case in cases:
        by_skill.setdefault(case.skill, []).append(case)

    for skill in ["pdf-creator", "project-assistant", "vision-assistant", "code-reviewer", "file-assistant"]:
        assert len(by_skill.get(skill, [])) >= 5


def test_given_mocked_skill_eval_when_run_then_metrics_are_reported():
    from scripts.eval_skills import EvalCase, evaluate_cases

    cases = [
        EvalCase(skill="pdf-creator", prompt="/pdf make report", expected_tool="create_pdf", required_terms=["PDF"]),
        EvalCase(skill="file-assistant", prompt="/files list Desktop", expected_tool="list_directory", required_terms=["Desktop"]),
    ]

    result = evaluate_cases(cases, responder=lambda case: {"tool": case.expected_tool, "answer": "PDF Desktop"})

    assert result["total"] == 2
    assert result["tool_accuracy"] == 1.0
    assert result["term_accuracy"] == 1.0
