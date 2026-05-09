from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def test_given_install_script_when_checked_then_one_command_bootstrap_installs_model_and_app():
    """
    GIVEN Josef runs the public installer
    WHEN the script is inspected
    THEN it bootstraps into Documents, installs Gemma 4 E4B and starts the local app.
    """
    script = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "MIMI_NOX_INSTALL_DIR:-$HOME/Documents/MiMi-Nox" in script
    assert "MIMI_NOX_MODEL:-gemma4:e4b" in script
    assert "git clone \"$REPO_URL\" \"$INSTALL_DIR\"" in script
    assert "pull \"$MODEL\"" in script
    assert "9.6 GB" in script
    assert "miminox start" in script
    assert "brew install python" in script
    assert "astral.sh/uv/install.sh" in script
    assert "python3-venv" in script
    assert "2.5 GB" not in script
    assert "No cloud" not in script


def test_given_install_scripts_when_parsed_then_shell_syntax_is_valid():
    """
    GIVEN install scripts are a critical first-run surface
    WHEN syntax is checked
    THEN macOS/Linux shell syntax is valid and Windows script exists.
    """
    subprocess.run(["bash", "-n", str(ROOT / "install.sh")], check=True)
    powershell_script = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "Python.Python.3.12" in powershell_script

    if shutil.which("pwsh"):
        subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"$null = [scriptblock]::Create((Get-Content -Raw '{ROOT / 'install.ps1'}'))"],
            check=True,
        )


def test_given_pyproject_when_loaded_then_miminox_cli_commands_are_exposed():
    """
    GIVEN the package metadata
    WHEN console scripts are checked
    THEN the new miminox CLI is installable without replacing the legacy TUI command.
    """
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]

    assert scripts["miminox"] == "miminox_cli:main"
    assert scripts["mimi-nox"] == "clawdash:main"
    assert "miminox_cli.py" in pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["include"]


def test_given_miminox_cli_when_help_requested_then_core_commands_exist():
    """
    GIVEN a user installs MiMi Nox
    WHEN the CLI help is shown
    THEN start, doctor and update are first-class commands.
    """
    result = subprocess.run(
        [sys.executable, str(ROOT / "miminox_cli.py"), "--help"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "start" in result.stdout
    assert "doctor" in result.stdout
    assert "update" in result.stdout


def test_given_miminox_doctor_when_model_is_listed_but_not_loadable_then_reports_repair_action(capsys):
    """
    GIVEN Ollama lists Gemma but a test generation fails
    WHEN miminox doctor runs
    THEN it reports the model as not loadable and tells the user how to repair it.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["doctor", "--model", "gemma4:e4b"])
    with patch("miminox_cli._ollama_binary", return_value="/usr/local/bin/ollama"), \
         patch("miminox_cli._model_installed", return_value=True), \
         patch("miminox_cli._json_get") as json_get, \
         patch("miminox_cli._model_loadable", return_value=(False, "unable to load model: missing blob")):
        json_get.side_effect = [
            {"models": [{"name": "gemma4:e4b"}]},
            {"status": "ok"},
        ]
        code = args.func(args)

    out = capsys.readouterr().out
    assert code == 1
    assert "Model gemma4:e4b load test" in out
    assert "repair: ollama pull gemma4:e4b" in out


def test_given_miminox_doctor_when_model_load_test_passes_then_setup_is_ok(capsys):
    """
    GIVEN Ollama is running and Gemma can generate a token
    WHEN miminox doctor runs
    THEN the local offline setup is considered healthy.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["doctor", "--model", "gemma4:e4b"])
    with patch("miminox_cli._ollama_binary", return_value="/usr/local/bin/ollama"), \
         patch("miminox_cli._model_installed", return_value=True), \
         patch("miminox_cli._json_get") as json_get, \
         patch("miminox_cli._model_loadable", return_value=(True, "test generation ok")):
        json_get.side_effect = [
            {"models": [{"name": "gemma4:e4b"}]},
            {"status": "ok"},
        ]
        code = args.func(args)

    out = capsys.readouterr().out
    assert code == 0
    assert "Model gemma4:e4b load test" in out
    assert "test generation ok" in out


def test_given_miminox_start_when_model_is_missing_then_it_pulls_before_starting(capsys):
    """
    GIVEN Gemma is missing after setup or cleanup
    WHEN miminox start is invoked
    THEN it pulls the local default model before launching the server.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["start", "--model", "gemma4:e4b", "--skip-model-check"])
    args.skip_model_check = False
    args.open = False
    args.reload = False
    args.host = "127.0.0.1"
    args.lan = False
    args.port = 8765

    with patch("miminox_cli._ensure_ollama_service", return_value=(True, "Ollama service is running")), \
         patch("miminox_cli._model_installed", return_value=False), \
         patch("miminox_cli._pull_model", return_value=(True, "pulled gemma4:e4b")) as pull_model, \
         patch("miminox_cli._model_loadable", return_value=(True, "test generation ok")), \
         patch("miminox_cli._run") as run:
        run.return_value.returncode = 0
        code = args.func(args)

    assert code == 0
    pull_model.assert_called_once_with("gemma4:e4b")
    assert "Model gemma4:e4b ready" in capsys.readouterr().out


def test_given_miminox_start_when_model_is_installed_but_broken_then_it_repairs_before_starting():
    """
    GIVEN Ollama has a listed but unloadable Gemma blob
    WHEN miminox start is invoked
    THEN it re-pulls once and only starts after the load test passes.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["start", "--model", "gemma4:e4b", "--skip-model-check"])
    args.skip_model_check = False
    args.open = False
    args.reload = False
    args.host = "127.0.0.1"
    args.lan = False
    args.port = 8765

    with patch("miminox_cli._ensure_ollama_service", return_value=(True, "Ollama service is running")), \
         patch("miminox_cli._model_installed", return_value=True), \
         patch("miminox_cli._model_loadable") as model_loadable, \
         patch("miminox_cli._pull_model", return_value=(True, "pulled gemma4:e4b")) as pull_model, \
         patch("miminox_cli._run") as run:
        model_loadable.side_effect = [
            (False, "unable to load model: missing blob"),
            (True, "test generation ok"),
        ]
        run.return_value.returncode = 0
        code = args.func(args)

    assert code == 0
    pull_model.assert_called_once_with("gemma4:e4b")
    assert model_loadable.call_count == 2


def test_given_miminox_start_lan_when_invoked_then_server_binds_to_all_interfaces():
    """
    GIVEN the user wants phone QR pairing
    WHEN miminox start --lan is invoked
    THEN the server starts on 0.0.0.0 while preserving local-model preflight.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["start", "--lan", "--skip-model-check"])

    with patch("miminox_cli._run") as run:
        run.return_value.returncode = 0
        code = args.func(args)
        cmd = run.call_args.args[0]
        env = run.call_args.kwargs["env"]

    assert code == 0
    assert cmd[cmd.index("--host") + 1] == "0.0.0.0"
    assert env["MIMI_NOX_HOST"] == "0.0.0.0"


def test_given_readme_quickstart_when_checked_then_first_path_is_one_command():
    """
    GIVEN a new user opens the README
    WHEN the Quick Start section is read
    THEN the first install path is exactly one terminal command.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = readme.split("## ⚡ Quick Start", 1)[1].split("<details>", 1)[0]
    bash_blocks = re.findall(r"```bash\n(.*?)\n```", quickstart, flags=re.DOTALL)

    assert bash_blocks
    first_command = bash_blocks[0].strip()
    assert first_command == "curl -fsSL https://raw.githubusercontent.com/MimiTechAi/mimi-nox/main/install.sh | bash"
    assert "\n" not in first_command
    assert "docker compose" not in quickstart.lower()


def test_given_readme_hero_when_checked_then_first_terminal_command_is_installer():
    """
    GIVEN a new user lands on GitHub
    WHEN they scan the hero and first success path
    THEN the first terminal command is the one-command offline-first installer, not Docker.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    bash_blocks = re.findall(r"```bash\n(.*?)\n```", readme, flags=re.DOTALL)

    assert bash_blocks
    assert bash_blocks[0].strip() == "curl -fsSL https://raw.githubusercontent.com/MimiTechAi/mimi-nox/main/install.sh | bash"
    assert "local AI assistant" in readme[:1500]
    assert "Optional online/API features are always opt-in" in readme[:1500]


def test_given_agent_instructions_when_checked_then_future_workflow_is_available():
    """
    GIVEN the user requested reusable 2026 engineering instructions
    WHEN repository agent guidance is checked
    THEN TDD, Git hygiene and frontend QA expectations are captured.
    """
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "offline-first" in content
    assert "WGT/TDD" in content
    assert "Root-PWA changes need desktop/mobile visual checks" in content
    assert "Git must not track" in content
