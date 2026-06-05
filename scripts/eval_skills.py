"""Local deterministic skill evals for MiMi Nox.

This runner intentionally avoids cloud calls. It can score mocked or future local
model responses against expected tool and required output terms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class EvalCase:
    skill: str
    prompt: str
    expected_tool: str = ""
    required_terms: list[str] = field(default_factory=list)


def load_eval_cases(root: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    if not root.exists():
        return cases
    for path in sorted(root.glob("*.yaml")):
        cases.extend(_parse_eval_file(path))
    return cases


def evaluate_cases(cases: list[EvalCase], responder: Callable[[EvalCase], dict]) -> dict:
    total = len(cases)
    if total == 0:
        return {"total": 0, "tool_accuracy": 0.0, "term_accuracy": 0.0}
    tool_hits = 0
    term_hits = 0
    for case in cases:
        result = responder(case)
        if result.get("tool") == case.expected_tool:
            tool_hits += 1
        answer = str(result.get("answer", "")).lower()
        if all(term.lower() in answer for term in case.required_terms):
            term_hits += 1
    return {
        "total": total,
        "tool_accuracy": tool_hits / total,
        "term_accuracy": term_hits / total,
    }


def _parse_eval_file(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    current: dict[str, object] | None = None
    list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "cases:":
            continue
        if stripped.startswith("- skill:"):
            if current:
                cases.append(_case_from_dict(current))
            current = {"skill": _value(stripped.split(":", 1)[1])}
            list_key = None
            continue
        if current is None:
            continue
        if stripped.startswith("- ") and list_key:
            values = current.setdefault(list_key, [])
            if isinstance(values, list):
                values.append(_value(stripped[2:]))
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                current[key] = []
                list_key = key
            elif value.startswith("[") and value.endswith("]"):
                current[key] = [_value(item) for item in value[1:-1].split(",") if item.strip()]
                list_key = None
            else:
                current[key] = _value(value)
                list_key = None
    if current:
        cases.append(_case_from_dict(current))
    return cases


def _value(text: str) -> str:
    return text.strip().strip("'\"")


def _case_from_dict(data: dict[str, object]) -> EvalCase:
    terms = data.get("required_terms", [])
    if isinstance(terms, str):
        terms = [terms]
    return EvalCase(
        skill=str(data.get("skill", "")),
        prompt=str(data.get("prompt", "")),
        expected_tool=str(data.get("expected_tool", "")),
        required_terms=[str(term) for term in terms],
    )


if __name__ == "__main__":
    loaded = load_eval_cases(Path("evals/skills"))
    print({"loaded_cases": len(loaded)})
