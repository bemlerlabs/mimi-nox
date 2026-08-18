"""P0-1 E1: Approval-Gates + Diff + --dry-run (conservative defaults).

Regression tests for the new approval/dry-run layer in `core/tools/approval.py`.
All tests are deterministic and offline; no mocks of the real tool layer.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make `core.tools.approval` importable regardless of CWD.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))


# ── Classification ─────────────────────────────────────────────────────────

def test_classification_safe_tools_do_not_need_approval():
    from core.tools.approval import classify_tool
    for name in ("read_file", "list_directory", "file_search", "get_datetime",
                 "query_source_notebook", "browser_screenshot"):
        assert classify_tool(name).auto_approve_by_default is True, name


def test_classification_mutating_tools_require_approval():
    from core.tools.approval import classify_tool
    for name in ("run_shell", "manage_tasks", "create_svg", "create_pdf",
                 "generate_chart", "create_pitch_deck", "create_pptx_deck"):
        assert classify_tool(name).auto_approve_by_default is False, name


def test_classification_shell_never_auto_approved():
    from core.tools.approval import classify_tool
    assert classify_tool("run_shell").auto_approve_by_default is False


# ── Dry-run: no side effects ───────────────────────────────────────────────

def test_dry_run_policy_blocks_execution():
    from core.tools.approval import ApprovalPolicy, request_approval

    policy = ApprovalPolicy(dry_run=True)
    decision = asyncio.run(request_approval("run_shell", {"command": "ls"}, policy))
    assert decision.approved is False
    assert decision.dry_run is True
    assert "ls" in decision.report
    assert "DRY-RUN" in decision.report.upper()


def test_dry_run_policy_blocks_svg_creation_no_file_written(tmp_path):
    from core.tools.approval import ApprovalPolicy, request_approval
    from core.tools.registry import execute_tool

    target = tmp_path / "no_write.svg"
    policy = ApprovalPolicy(dry_run=True)
    result = asyncio.run(execute_tool(
        "create_svg",
        {"svg_code": "<svg><rect/></svg>", "filename": target.name},
        policy=policy,
    ))
    # Dry-run must NOT write the file.
    assert not target.exists()
    assert "DRY-RUN" in result.upper() or "[dry-run]" in result.lower()


def test_executing_with_policy_yes_writes_svg(tmp_path, monkeypatch):
    from core.tools.approval import ApprovalPolicy
    from core.tools.registry import execute_tool

    monkeypatch.setenv("HOME", str(tmp_path))
    policy = ApprovalPolicy(auto_approve=True)
    result = asyncio.run(execute_tool(
        "create_svg",
        {"svg_code": "<svg><rect width='10' height='10'/></svg>",
         "filename": "proof_yes.svg"},
        policy=policy,
    ))
    written = tmp_path / "Downloads" / "proof_yes.svg"
    assert written.exists(), f"expected {written} to exist, got: {result!r}"


def test_executing_with_policy_no_blocks_execution(tmp_path, monkeypatch):
    from core.tools.approval import ApprovalPolicy
    from core.tools.registry import execute_tool

    monkeypatch.setenv("HOME", str(tmp_path))

    async def deny(_name, _args):
        return False

    policy = ApprovalPolicy(auto_approve=False, on_confirm=deny)
    result = asyncio.run(execute_tool(
        "create_svg",
        {"svg_code": "<svg><rect/></svg>", "filename": "proof_no.svg"},
        policy=policy,
    ))
    written = tmp_path / "Downloads" / "proof_no.svg"
    assert not written.exists()
    assert "Abgelehnt" in result or "abgelehnt" in result.lower()


def test_safe_tools_bypass_policy_even_without_auto_approve(tmp_path, monkeypatch):
    from core.tools.approval import ApprovalPolicy
    from core.tools.registry import execute_tool

    # read_file on a file in the allowed roots must work with a strict policy
    # (SAFE tools never need approval).
    target = tmp_path / "allow.txt"
    target.write_text("ok\n")
    policy = ApprovalPolicy(auto_approve=False)

    async def deny(_n, _a):
        return False

    policy.on_confirm = deny
    result = asyncio.run(execute_tool("read_file", {"path": str(target)}, policy=policy))
    assert "ok" in result


def test_policy_yes_overrides_deny_callback():
    """`--yes` is a CLI override; even a strict deny-callback yields when auto_approve."""
    from core.tools.approval import ApprovalPolicy, request_approval

    async def deny(_n, _a):
        return False

    policy = ApprovalPolicy(auto_approve=True, on_confirm=deny)
    decision = asyncio.run(request_approval("create_svg", {"filename": "x"}, policy))
    assert decision.approved is True


# ── Diff ────────────────────────────────────────────────────────────────────

def test_format_diff_for_svg_shows_preview():
    from core.tools.approval import format_diff
    d = format_diff("create_svg", {"svg_code": "<svg><rect width='1' height='1'/></svg>",
                                   "filename": "x.svg"})
    assert "x.svg" in d
    assert "<svg>" in d


def test_format_diff_for_shell_shows_command():
    from core.tools.approval import format_diff
    d = format_diff("run_shell", {"command": "ls -la"})
    assert "ls -la" in d


# ── Non-interactive guard ───────────────────────────────────────────────────

def test_non_interactive_requires_explicit_flag():
    """A MUTATING tool with no policy + non-interactive TTY must refuse (raise)."""
    from core.tools.approval import ApprovalPolicy, request_approval

    policy = ApprovalPolicy(auto_approve=False, interactive=False)
    decision = asyncio.run(request_approval("run_shell", {"command": "rm -rf /"}, policy))
    assert decision.approved is False
    assert "interaktiv" in decision.report or "INTERACTIVE" in decision.report.upper() or \
        "--yes" in decision.report or "non-interactive" in decision.report.lower()


def test_policy_defaults_conservative():
    """No auto-approval, no dry-run, strict on_confirm by default (E1 mitigation)."""
    from core.tools.approval import ApprovalPolicy
    p = ApprovalPolicy()
    assert p.auto_approve is False
    assert p.dry_run is False


# ── CLI: argparse surface ──────────────────────────────────────────────────

def test_cli_tool_subcommand_parses_dry_run():
    import miminox_cli
    parser = miminox_cli.build_parser()
    args = parser.parse_args(["tool", "create_svg",
                              "--arg", "filename=proof_dry.svg",
                              "--arg", "svg_code=<svg><rect/></svg>",
                              "--dry-run"])
    assert args.command == "tool"
    assert args.tool_name == "create_svg"
    assert args.dry_run is True
    assert args.yes is False


def test_cli_tool_subcommand_parses_yes():
    import miminox_cli
    parser = miminox_cli.build_parser()
    args = parser.parse_args(["tool", "run_shell",
                              "--arg", "command=echo hi",
                              "--yes"])
    assert args.yes is True
    assert args.dry_run is False


def test_cli_tool_subcommand_yes_no_mutually_exclusive():
    import miminox_cli
    parser = miminox_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["tool", "run_shell", "--arg", "command=echo",
                           "--yes", "--no"])


def test_cli_tool_subcommand_requires_name():
    import miminox_cli
    parser = miminox_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["tool"])


# ── E2E: CLI subprocess dry-run leaves workspace clean ────────────────────

def test_e2e_cli_tool_dry_run_creates_no_file(tmp_path, monkeypatch):
    """Run `miminox tool create_svg --dry-run` via real CLI subprocess.

    HOME is pointed at tmp_path so no real files are touched.
    The target SVG must NOT be created on disk.
    """
    env = {**os.environ, "HOME": str(tmp_path)}
    target = "proof_e2e_dry.svg"
    proc = subprocess.run(
        [sys.executable, str(_REPO / "miminox_cli.py"),
         "tool", "create_svg",
         "--arg", f"filename={target}",
         "--arg", "svg_code=<svg><rect/></svg>",
         "--dry-run"],
        cwd=str(_REPO), env=env, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    assert (tmp_path / "Downloads" / target).exists() is False
    assert "DRY-RUN" in proc.stdout.upper() or "[dry-run]" in proc.stdout.lower()


def test_e2e_cli_tool_yes_writes_file(tmp_path, monkeypatch):
    """The same call WITHOUT --dry-run but WITH --yes writes the file."""
    env = {**os.environ, "HOME": str(tmp_path)}
    target = "proof_e2e_yes.svg"
    proc = subprocess.run(
        [sys.executable, str(_REPO / "miminox_cli.py"),
         "tool", "create_svg",
         "--arg", f"filename={target}",
         "--arg", "svg_code=<svg><rect/></svg>",
         "--yes"],
        cwd=str(_REPO), env=env, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    assert (tmp_path / "Downloads" / target).exists()


def test_e2e_cli_tool_without_flag_in_noninteractive_blocks(tmp_path, monkeypatch):
    """Default = conservative: a non-interactive call without --yes/--dry-run
    must NOT execute a mutating tool and must return exit code 1."""
    env = {**os.environ, "HOME": str(tmp_path), "CI": "1"}
    target = "proof_e2e_default.svg"
    proc = subprocess.run(
        [sys.executable, str(_REPO / "miminox_cli.py"),
         "tool", "create_svg",
         "--arg", f"filename={target}",
         "--arg", "svg_code=<svg><rect/></svg>"],
        cwd=str(_REPO), env=env, capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL,
    )
    assert proc.returncode != 0
    assert (tmp_path / "Downloads" / target).exists() is False
