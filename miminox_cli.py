"""Command line helper for the MiMi Nox local web app."""
from __future__ import annotations

import argparse
import builtins
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

try:
    from core._version import __version__ as MIMI_NOX_VERSION
except Exception:  # standalone source-tree run without the core/ package
    MIMI_NOX_VERSION = "4.0.0"


# Hardware-adaptive Default-Modellwahl (RAM-basiert).
# Die Wahl bleibt dem User überlassen: MIMI_NOX_MODEL / CLI --model überschreibt.
try:
    from core.model_config import recommended_fast_model
    DEFAULT_MODEL = recommended_fast_model()
except Exception:
    # Fallback für standalone-Aufruf ohne core/ Paket.
    try:
        import psutil
        _ram = psutil.virtual_memory().total / (1024**3)
        DEFAULT_MODEL = "gemma4:12b" if _ram >= 16 else ("gemma4:e4b" if _ram >= 8 else "gemma4:e2b")
    except Exception:
        DEFAULT_MODEL = "gemma4:e4b"  # unbekannte HW → konservatives kleines Modell

# Engine-Auswahl-Persistenz (core/engine_config.py): `miminox tui` startbar
# ohne Modell-Flag — der User wählt einmal seine Engine, die Konfig wird
# nach ~/.mimi-nox/engine.json hinterlegt und bei jedem Start wiederverwendet.
try:
    from core.engine_config import (
        EngineChoice,
        OPENAI_COMPAT,
        load_engine_config,
        save_engine_config,
    )
except Exception:  # standalone source-tree run ohne core/ Paket
    class EngineChoice:  # type: ignore
        """Defensiver Shim – funktional identisch zum realen Modul."""

        def __init__(self, provider: str, model: str, api_url: str | None = None) -> None:
            self.provider = provider
            self.model = model
            self.api_url = api_url

        def to_flags(self) -> list[str]:
            flags = ["--model", self.model]
            if self.api_url:
                flags += ["--api-url", self.api_url]
            return flags

        def apply_env(self) -> None:
            os.environ["MIMI_NOX_MODEL"] = self.model
            if self.api_url:
                os.environ["MIMI_OPENAI_COMPAT_BASE_URL"] = self.api_url

    OPENAI_COMPAT = "openai_compatible"
    load_engine_config = lambda *a, **k: None  # type: ignore
    save_engine_config = lambda *a, **k: False  # type: ignore
DEFAULT_PORT = 8765
LOCAL_OLLAMA_HOST = "127.0.0.1:11434"
LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
PROJECT_ROOT = Path(__file__).resolve().parent


def _ollama_binary() -> str | None:
    candidates = [
        "/Applications/Ollama.app/Contents/Resources/ollama",
        "/opt/homebrew/opt/ollama/bin/ollama",
        "/opt/homebrew/bin/ollama",
        "/usr/local/bin/ollama",
        shutil.which("ollama"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def _ollama_model_candidates(model: str) -> list[str]:
    candidates = [model]
    if sys.platform == "darwin" and model == "gemma4:12b":
        candidates.extend(["gemma4:12b-mlx", "gemma4:12b-nvfp4"])
    return list(dict.fromkeys(candidates))


def _run(
    cmd: list[str],
    *,
    check: bool = False,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        env=env,
        check=check,
        capture_output=capture_output,
    )


def _ollama_env() -> dict[str, str]:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = LOCAL_OLLAMA_HOST
    return env


def _local_ollama_detected() -> bool:
    """Fail-safe Check: läuft eine lokale Ollama-Engine? (offline-first Erkennung)."""
    return _json_get(f"{LOCAL_OLLAMA_BASE_URL}/api/tags", timeout=1.0) is not None


def _json_get(url: str, timeout: float = 3.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _json_post(url: str, payload: dict, timeout: float = 20.0) -> dict | None:
    try:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _model_installed(model: str) -> bool:
    ollama = _ollama_binary()
    if not ollama:
        return False
    result = subprocess.run(
        [ollama, "show", model],
        text=True,
        env=_ollama_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _model_loadable(model: str) -> tuple[bool, str]:
    response = _json_post(
        f"{LOCAL_OLLAMA_BASE_URL}/api/generate",
        {"model": model, "prompt": "OK", "stream": False, "options": {"num_predict": 1}},
        timeout=30.0,
    )
    if response is None:
        return False, "could not generate a test token"
    if response.get("error"):
        return False, str(response["error"])
    return True, "test generation ok"


def _wait_for_ollama_service(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _json_get(f"{LOCAL_OLLAMA_BASE_URL}/api/tags", timeout=1.0) is not None:
            return True
        time.sleep(0.5)
    return False


def _ensure_ollama_service() -> tuple[bool, str]:
    if _json_get(f"{LOCAL_OLLAMA_BASE_URL}/api/tags", timeout=1.0) is not None:
        return True, "Ollama service is running"

    ollama = _ollama_binary()
    if not ollama:
        return False, "Ollama CLI not found. Run install.sh or install Ollama first."

    subprocess.Popen(
        [ollama, "serve"],
        cwd=PROJECT_ROOT,
        env=_ollama_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if _wait_for_ollama_service():
        return True, "Ollama service started"
    return False, f"Ollama service did not become ready on {LOCAL_OLLAMA_BASE_URL}"


def _pull_model(model: str) -> tuple[bool, str]:
    ollama = _ollama_binary()
    if not ollama:
        return False, "Ollama CLI not found"

    saw_version_error = False
    attempted_upgrade = False
    for candidate in _ollama_model_candidates(model):
        result = subprocess.run(
            [ollama, "pull", candidate],
            cwd=PROJECT_ROOT,
            text=True,
            env=_ollama_env(),
            capture_output=True,
        )
        if result.returncode == 0:
            suffix = "" if candidate == model else f" as {candidate}"
            return True, f"pulled {model}{suffix}"
        combined = f"{result.stdout or ''}\n{result.stderr or ''}"
        if "requires a newer version of Ollama" not in combined:
            continue
        saw_version_error = True
        if attempted_upgrade:
            continue
        attempted_upgrade = True
        upgraded, upgrade_detail = _upgrade_ollama()
        if not upgraded:
            continue
        ollama = _ollama_binary()
        if not ollama:
            return False, "Ollama updated but CLI not found"
        retry = subprocess.run(
            [ollama, "pull", candidate],
            cwd=PROJECT_ROOT,
            text=True,
            env=_ollama_env(),
            capture_output=True,
        )
        if retry.returncode == 0:
            suffix = "" if candidate == model else f" as {candidate}"
            return True, f"pulled {model}{suffix} after Ollama update"
    if saw_version_error:
        version_detail = _ollama_version_detail(_ollama_binary())
        return False, (
            "Ollama is still too old for this Gemma 4 manifest. "
            f"Install the latest Ollama from https://ollama.com/download and retry. {version_detail}"
        )
    return False, f"ollama pull {model} failed"


def _upgrade_ollama() -> tuple[bool, str]:
    if sys.platform == "darwin":
        if not shutil.which("brew"):
            return False, "Ollama is too old. Install the latest version from https://ollama.com/download"
        if subprocess.run(["brew", "list", "--formula", "ollama"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            subprocess.run(["brew", "uninstall", "--formula", "ollama"], cwd=PROJECT_ROOT, text=True)
        commands = [
            ["brew", "reinstall", "--cask", "ollama-app"],
            ["brew", "upgrade", "--cask", "ollama-app"],
            ["brew", "install", "--cask", "ollama-app"],
            ["brew", "reinstall", "--cask", "ollama"],
            ["brew", "upgrade", "--cask", "ollama"],
            ["brew", "install", "--cask", "ollama"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=PROJECT_ROOT, text=True)
            if result.returncode == 0:
                subprocess.run(["pkill", "-x", "Ollama"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", "ollama serve"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)
                _ensure_ollama_service()
                return True, "Ollama updated"
        return False, "Ollama update failed via Homebrew; install latest from https://ollama.com/download"

    result = subprocess.run(
        ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode == 0:
        return True, "Ollama updated"
    return False, "Ollama update failed"


def _ollama_version_detail(ollama: str | None) -> str:
    if not ollama:
        return "Ollama CLI not found."
    result = subprocess.run([ollama, "--version"], cwd=PROJECT_ROOT, text=True, capture_output=True)
    output = (result.stdout or result.stderr or "").strip()
    return f"Current CLI: {output}" if output else f"Current CLI: {ollama}"


def _venv_python() -> str:
    candidate = PROJECT_ROOT / ".venv" / "bin" / "python"
    return str(candidate) if candidate.exists() else sys.executable


def _repair_repo() -> tuple[bool, str]:
    if not (PROJECT_ROOT / ".git").exists():
        return True, "not a git checkout"

    status = _run(["git", "status", "--short"], env=os.environ.copy(), capture_output=True)
    if status.returncode != 0:
        return False, "could not inspect git status"
    if (status.stdout or "").strip():
        return False, "local changes present; skip git pull to protect your work"

    fetch = _run(["git", "fetch", "--quiet", "origin"], env=os.environ.copy())
    if fetch.returncode != 0:
        return False, "git fetch failed"

    branch = _run(["git", "branch", "--show-current"], env=os.environ.copy(), capture_output=True)
    branch_name = (branch.stdout or "").strip() if branch.returncode == 0 else ""
    if not branch_name:
        return True, "detached HEAD; skip auto-update"

    behind = _run(["git", "rev-list", "--count", f"HEAD..origin/{branch_name}"], env=os.environ.copy(), capture_output=True)
    if behind.returncode != 0:
        return False, "could not compare with origin"
    if (behind.stdout or "").strip() in ("", "0"):
        return True, "repo up to date"

    pull = _run(["git", "pull", "--ff-only"], env=os.environ.copy())
    if pull.returncode != 0:
        return False, "git pull --ff-only failed"
    return True, "repo updated"


def _repair_dependencies() -> tuple[bool, str]:
    if not (PROJECT_ROOT / "pyproject.toml").exists():
        return False, "pyproject.toml missing"
    cmd = [_venv_python(), "-m", "pip", "install", "-e", ".[gui,voice]"]
    result = _run(cmd, env=os.environ.copy())
    if result.returncode == 0:
        return True, "dependencies installed"
    return False, "dependency install failed"


def _ensure_model_ready_for_start(model: str) -> tuple[bool, str]:
    service_ok, service_detail = _ensure_ollama_service()
    if not service_ok:
        return False, service_detail

    if not _model_installed(model):
        pulled, pull_detail = _pull_model(model)
        if not pulled:
            return False, pull_detail

    ready, detail = _model_loadable(model)
    if ready:
        return True, detail

    pulled, pull_detail = _pull_model(model)
    if not pulled:
        return False, f"{detail}; repair failed: {pull_detail}"

    ready, detail = _model_loadable(model)
    if ready:
        return True, f"{pull_detail}; {detail}"
    return False, f"{pull_detail}; still not loadable: {detail}"


def _print_check(ok: bool, label: str, detail: str = "") -> None:
    status = "OK" if ok else "MISSING"
    suffix = f" - {detail}" if detail else ""
    print(f"{status:7} {label}{suffix}")


def _run_doctor_repairs(args: argparse.Namespace) -> list[tuple[str, bool, str]]:
    repairs: list[tuple[str, bool, str]] = []
    if os.environ.get("OLLAMA_HOST") not in (None, "", LOCAL_OLLAMA_HOST, LOCAL_OLLAMA_BASE_URL):
        repairs.append(("Normalize OLLAMA_HOST", True, f"MiMi commands use {LOCAL_OLLAMA_HOST}; shell value is ignored"))

    repo_ok, repo_detail = _repair_repo()
    repairs.append(("Repair repo", repo_ok, repo_detail))

    deps_ok, deps_detail = _repair_dependencies()
    repairs.append(("Repair dependencies", deps_ok, deps_detail))

    model_ok, model_detail = _ensure_model_ready_for_start(args.model)
    repairs.append((f"Repair model {args.model}", model_ok, model_detail))
    return repairs


def cmd_doctor(args: argparse.Namespace) -> int:
    repairs: list[tuple[str, bool, str]] = []
    if args.fix:
        repairs = _run_doctor_repairs(args)

    checks: list[tuple[str, bool, str]] = []
    ollama = _ollama_binary()
    checks.append(("Python", sys.version_info >= (3, 10), sys.version.split()[0]))
    checks.append(("Project files", (PROJECT_ROOT / "app" / "index.html").exists(), str(PROJECT_ROOT)))
    checks.append(("Ollama CLI", bool(ollama), ollama or "not in PATH"))

    ollama_running = False
    local_models: list[str] = []
    tags = _json_get(f"{LOCAL_OLLAMA_BASE_URL}/api/tags")
    if tags is not None:
        ollama_running = True
        local_models = [item.get("name", "") for item in tags.get("models", [])]
    checks.append(("Ollama service", ollama_running, LOCAL_OLLAMA_BASE_URL))

    model_installed = _model_installed(args.model)
    model_ready = False
    model_detail = "run: miminox update --model " + args.model
    if model_installed and ollama_running:
        model_ready, model_detail = _model_loadable(args.model)
        if not model_ready:
            model_detail = f"{model_detail}; repair: ollama pull {args.model}"
    elif model_installed:
        model_detail = "installed; start Ollama to verify loadability"
    checks.append((f"Model {args.model}", model_installed, "installed" if model_installed else model_detail))
    checks.append((f"Model {args.model} load test", model_ready, model_detail))

    server_health = _json_get(f"http://127.0.0.1:{args.port}/api/health")
    checks.append(("MiMi Nox server", server_health is not None, f"http://127.0.0.1:{args.port}"))

    payload = {
        "ok": all(ok for _, ok, _ in checks[:-1]) and model_ready and all(ok for _, ok, _ in repairs),
        "repairs": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in repairs],
        "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
        "local_models": local_models,
        "server": server_health,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if repairs:
            for name, ok, detail in repairs:
                _print_check(ok, name, detail)
            print("")
        for name, ok, detail in checks:
            _print_check(ok, name, detail)
        if local_models:
            print("Models  " + ", ".join(local_models))
        total = len(checks) + len(repairs)
        passed = sum(1 for _, ok, _ in checks if ok) + sum(1 for _, ok, _ in repairs if ok)
        print(f"Summary: {passed}/{total} checks OK")
    return 0 if payload["ok"] else 1


def cmd_start(args: argparse.Namespace) -> int:
    if not args.skip_model_check:
        ready, detail = _ensure_model_ready_for_start(args.model)
        _print_check(ready, f"Model {args.model} ready", detail)
        if not ready:
            return 1

    env = os.environ.copy()
    env["OLLAMA_HOST"] = LOCAL_OLLAMA_HOST
    env["MIMI_NOX_MODEL"] = args.model
    env.setdefault("MIMI_LOCAL_OLLAMA_BASE_URL", LOCAL_OLLAMA_BASE_URL)
    host = "0.0.0.0" if args.lan else args.host
    env["MIMI_NOX_HOST"] = host
    env["MIMI_NOX_PORT"] = str(args.port)
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_server.py"),
        "--host",
        host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")

    if args.open:
        process = subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env)
        browser_host = "127.0.0.1" if host == "0.0.0.0" else host
        url = f"http://{browser_host}:{args.port}"
        for _ in range(30):
            if _json_get(f"{url}/api/health", timeout=1.0) is not None:
                webbrowser.open(url)
                break
            time.sleep(1)
        return process.wait()

    return _run(cmd, env=env).returncode


def cmd_update(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps({"ok": True, "message": "update gestartet"}, indent=2))
    if (PROJECT_ROOT / ".git").exists():
        _run(["git", "pull", "--ff-only"])

    installer = PROJECT_ROOT / "install.sh"
    if not installer.exists():
        _emit_error(args, 1, "install.sh nicht gefunden", "Projekt-Verzeichnis prüfen oder `git pull` ausführen")
        return 1

    env = os.environ.copy()
    env["OLLAMA_HOST"] = LOCAL_OLLAMA_HOST
    env["MIMI_NOX_MODEL"] = args.model
    env["MIMI_NOX_NO_START"] = "1"
    rc = _run(["bash", str(installer), "--no-start"], env=env).returncode
    if args.json:
        print(json.dumps({"ok": rc == 0, "exit_code": rc}, indent=2))
    return rc


# ── Phase 1: Shell-Completions (DX) ───────────────────────────────────────────
# Generiert statische Completions-Skripte für bash/zsh/fish. Die Subcommand-Liste
# wird aus build_parser() abgeleitet, damit neue Subcommands automatisch
# auftauchen (kein Duplikat von Parser-Wissen).

_COMPLETION_SHELLS = ("bash", "zsh", "fish")


def _completion_subcommands() -> list[str]:
    names = []
    for action in build_parser()._actions:
        if getattr(action, "choices", None) is not None:
            names = sorted(action.choices)
    return names or ["start", "doctor", "update", "tui", "completion"]


def _completion_script(shell: str, cmds: list[str]) -> str:
    joined = " ".join(cmds)
    if shell == "bash":
        return (
            f"# bash completion for miminox\n"
            f"_miminox_complete() {{\n"
            f"    local cur=\"${{COMP_WORDS[COMP_CWORD]}}\"\n"
            f"    COMPREPLY=( $(compgen -W '{joined}' -- \"$cur\") )\n"
            f"}}\n"
            f"complete -F _miminox_complete miminox\n"
        )
    if shell == "zsh":
        quoted = " ".join(f'"{c}"' for c in cmds)
        return (
            f"#compdef miminox\n"
            f"_miminox() {{\n"
            f"    local -a cmds\n"
            f"    cmds=({quoted})\n"
            f"    _describe 'command' cmds\n"
            f"}}\n"
            f"compdef _miminox miminox\n"
        )
    # fish
    return (
        f"# fish completion for miminox\n"
        f"complete -c miminox -f -n 'not __fish_use_subcommand' \\\n"
        f"  -a '{joined}' -d 'command'\n"
    )


def cmd_completion(args: argparse.Namespace) -> int:
    shell = (args.shell or "").lower()
    if shell not in _COMPLETION_SHELLS:
        _emit_error(
            args,
            2,
            f"Unbekannte Shell: {shell!r}",
            f"Verfügbar: {', '.join(_COMPLETION_SHELLS)} (z.B. `miminox completion bash`)",
        )
        return 2
    print(_completion_script(shell, _completion_subcommands()), end="")
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    """Phase 2 Item 7: Multi-Session-Verwaltung.

    Subkommandos: list / new / switch / rm / rename.
    Lazy-Import von core.multi_session (standalone-Lauf bleibt robust).
    """
    try:
        from core import multi_session as ms
    except ImportError as e:
        _emit_error(
            args,
            1,
            f"Multi-Session nicht verfügbar: {e}",
            "Installiere das vollständige Package: `pip install -e .`",
        )
        return 1

    action = args.session_action
    as_json = getattr(args, "json", False)

    if action == "list":
        sessions = ms.list_sessions()
        if as_json:
            print(json.dumps(sessions, ensure_ascii=False, indent=2))
            return 0
        if not sessions:
            print("Keine Sessions. Lege mit `miminox session new <Titel>` an.")
            return 0
        active_id = ms.get_active_id()
        print("Sessions (neueste zuerst):")
        for s in sessions:
            marker = "●" if s.get("id") == active_id else " "
            info = ms.session_info(s["id"]) or {}
            print(
                f" {marker} {s.get('id'):<8}  {s.get('title', '?'):<30}  "
                f"Nachrichten: {info.get('message_count', 0):>3}   "
                f"Update: {info.get('updated_at', '')[:19]}"
            )
        return 0

    if action == "new":
        if not args.title:
            _emit_error(
                args, 2,
                "`miminox session new` erwartet einen Titel.",
                "Beispiel: `miminox session new --title 'Projekt Alpha'`",
            )
            return 2
        entry = ms.create_session(args.title)
        ms.switch_to(entry["id"])
        if as_json:
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            print(f"Neue Session: {entry['id']} („{entry['title']}")
        return 0

    if action == "switch":
        if not args.id:
            _emit_error(
                args, 2,
                "`miminox session switch` erwartet eine Session-ID.",
                "IDs siehst du mit `miminox session list`.",
            )
            return 2
        if ms.get_session(args.id) is None:
            _emit_error(
                args, 2,
                f"Session „{args.id}“ nicht gefunden.",
                "IDs: `miminox session list`",
            )
            return 2
        ms.switch_to(args.id)
        if as_json:
            print(json.dumps({"active_id": ms.get_active_id()}, indent=2))
        else:
            print(f"Aktive Session: {ms.get_active_id()}")
        return 0

    if action == "rm":
        if not args.id:
            _emit_error(
                args, 2,
                "`miminox session rm` erwartet eine Session-ID.",
                "IDs siehst du mit `miminox session list`.",
            )
            return 2
        if ms.get_session(args.id) is None:
            _emit_error(
                args, 2,
                f"Session „{args.id}“ nicht gefunden.",
                "IDs: `miminox session list`",
            )
            return 2
        ms.delete_session(args.id)
        if as_json:
            print(json.dumps({"deleted": args.id}, indent=2))
        else:
            print(f"Session „{args.id}“ gelöscht.")
        return 0

    if action == "rename":
        if not args.id or not args.title:
            _emit_error(
                args, 2,
                "`miminox session rename` erwartet ID und neuen Titel.",
                "Beispiel: `miminox session rename --id abc12345 --title 'Neuer Name'`",
            )
            return 2
        if ms.get_session(args.id) is None:
            _emit_error(
                args, 2,
                f"Session „{args.id}“ nicht gefunden.",
                "IDs: `miminox session list`",
            )
            return 2
        ms.rename_session(args.id, args.title)
        if as_json:
            print(json.dumps(ms.get_session(args.id), ensure_ascii=False, indent=2))
        else:
            print(f"Session „{args.id}“ heißt jetzt „{args.title}“.")
        return 0

    _emit_error(args, 2, f"Unbekannte Session-Aktion: {action!r}",
               "Verfügbar: list · new · switch · rm · rename")
    return 2


def _emit_error(args: argparse.Namespace, code: int, message: str, fix: str = "") -> None:
    """Actionable Errors (DX): klare Cause+Fix, nie roher Stacktrace. Mit --json
    ein stabiles Machine-readable Format, ohne Secrets."""
    # Phase 4 Item 15: stabile maschinenlesbare Error-Codes (code_id) neben dem
    # numerischen Exit-Code. Mapping: 2 → usage_error, sonst runtime_error.
    try:
        from core.observability import ErrorCode  # lazy: standalone-Lauf bleibt robust

        code_id = ErrorCode.USAGE.value if code == 2 else ErrorCode.RUNTIME.value
    except Exception:
        code_id = "usage_error" if code == 2 else "runtime_error"
    if getattr(args, "json", False):
        print(json.dumps({"error": {"code": code, "code_id": code_id, "message": message, "fix": fix}}, indent=2))
    else:
        print(f"Error: {message}", file=sys.stderr)
        if fix:
            print(f"  Fix: {fix}", file=sys.stderr)


def _run_engine_onboarding(
    input_fn=builtins.input, config_path=None
) -> Any:
    """Interaktive Engine-Auswahl (Onboarding) für `miminox tui`.

    Der User wählt einmal seine Engine (lokale Ollama / eigene Ollama- oder
    vLLM-Engine / DGX-Spark ds4 / OpenAI-kompatible API). Die Wahl wird nach
    ~/.mimi-nox/engine.json hinterlegt und bei jedem Start wiederverwendet.
    API-Keys werden NIEMALS persistiert, sondern nur als Session-Env gesetzt.
    """
    print("◑ MiMi Nox – Engine-Auswahl (einmalig, wird gespeichert)")
    print("  Jeder User wählt seine eigene Engine:")
    print("  [1] Lokale Ollama            (Default, offline-first) → gemma4:12b")
    print("  [2] Eigene Ollama / vLLM     (Remote-URL, OpenAI-kompatibel)")
    print("  [3] DGX-Spark ds4            (OpenAI-kompatibel, vLLM)")
    print("  [4] OpenAI-kompatible API    (z.B. Mistral / OpenAI)")

    if _local_ollama_detected():
        print("  ✓ Lokale Ollama-Engine erkannt – offline-first")
    else:
        print("  ⚠ Keine lokale Engine erkannt – bitte Engine und ggf. URL wählen")

    while True:
        try:
            raw = (input_fn("Engine [1/2/3/4, Default 1]: ") or "1").strip()
            if raw in ("1", "local"):
                provider = "local_ollama"
                default_model = DEFAULT_MODEL
                api_url = None
            elif raw in ("2", "custom"):
                provider = "custom_ollama"
                default_model = DEFAULT_MODEL
                api_url = _ask_url(
                    input_fn,
                    "Engine-Basis-URL (z.B. http://10.0.0.50:11434/v1): ",
                    required=True,
                )
            elif raw in ("3", "dgx", "spark"):
                provider = OPENAI_COMPAT
                default_model = "deepseek-v4-flash"
                api_url = _ask_url(
                    input_fn,
                    "DGX-Spark ds4 URL (z.B. http://spark-...:8000/v1): ",
                    required=True,
                )
            elif raw in ("4", "api"):
                provider = OPENAI_COMPAT
                default_model = "custom-model"
                api_url = _ask_url(
                    input_fn,
                    "OpenAI-kompatible Basis-URL (z.B. https://api.mistral.ai/v1): ",
                    required=True,
                )
                key = (input_fn("API-Key (optional, wird NICHT gespeichert): ") or "").strip()
                if key:
                    os.environ["MIMI_OPENAI_COMPAT_API_KEY"] = key
            else:
                print(f"  Unbekannte Wahl: {raw!r} – bitte 1/2/3/4.")
                continue
            break
        except (EOFError, KeyboardInterrupt):
            print("\n  Abbruch – Engine-Auswahl übersprungen, lokale Ollama wird genutzt.")
            provider = "local_ollama"
            default_model = DEFAULT_MODEL
            api_url = None
            break

    try:
        model = (input_fn(f"Modell [Default {default_model}]: ") or default_model).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Abbruch – Default-Modell wird genutzt.")
        model = default_model
    if not model:
        model = default_model

    choice = EngineChoice(provider=provider, model=model, api_url=api_url)
    saved = save_engine_config(choice, config_path)
    print(f"  → Engine gespeichert: {provider} / {model}"
          + (f" @ {api_url}" if api_url else ""))
    if not saved:
        print("  ⚠  Konfig konnte nicht geschrieben werden – Auswahl gilt nur für diesen Start.")
    return choice


def _ask_url(input_fn, prompt: str, required: bool = False) -> str | None:
    """Liest eine Engine-Basis-URL; None bei Abbruch/leer und nicht required."""
    while True:
        try:
            url = input_fn(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return None if not required else _abort_url()
        if url:
            return url
        if required:
            print("  ⚠ URL ist für diese Engine erforderlich – bitte erneut eingeben.")
            continue
        return None


def _abort_url() -> str:
    raise SystemExit("Abbruch: Engine-Basis-URL erforderlich für diese Auswahl.")


def cmd_tui(args: argparse.Namespace, config_path=None) -> int:
    import miminox

    # Explizite Flags gewinnen immer → kein Onboarding nötig.
    if args.model or args.api_url:
        forwarded = ["mimi-nox"]
        if args.model:
            forwarded.extend(["--model", args.model])
        if args.api_url:
            forwarded.extend(["--api-url", args.api_url])
        if args.reset:
            forwarded.append("--reset")
    else:
        # Ohne Modell-Flag: persistierte Engine-Auswahl nutzen.
        # Standard = Qwen-DGX (User-Mandat 2026-08-18). Kein Ollama-Pull.
        # Onboarding läuft NUR bei --configure (END-USER wählt Provider).
        choice: Any = None
        if not args.configure:
            choice = load_engine_config(config_path)
            if choice is None:
                from core.engine_config import default_engine_choice
                choice = default_engine_choice()
        else:
            # --configure: END-USER wählt Provider (Ollama / eigener Endpoint / OpenRouter)
            choice = _run_engine_onboarding(config_path=config_path)
        choice.apply_env()
        forwarded = ["mimi-nox"] + choice.to_flags()
        if args.reset:
            forwarded.append("--reset")

    # P0-1 E1: Approval-Flags an die TUI weiterreichen
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.yes:
        forwarded.append("--yes")
    if args.no:
        forwarded.append("--no")

    old_argv = sys.argv
    try:
        sys.argv = forwarded
        miminox.main()
    finally:
        sys.argv = old_argv
    return 0


# ── P0-1 E1: Deterministischer Tool-Modus (Approval / Diff / --dry-run) ────

def _parse_tool_args(pairs: list[str]) -> dict:
    """Parse --arg k=v Pairs zu einem Dict. Werte als String (Tool-typisiert
    über das JSON-Schema des Tools; hier bewusst simpel für CLI-Usage)."""
    out: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"Ungültiges --arg-Format: '{pair}' (erwartet: key=value)")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Leerer --arg-Key: '{pair}'")
        # JSON-Interpretation versuchen (listen/numbers/bools), sonst String
        try:
            out[key] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            out[key] = value
    return out


def cmd_tool(args: argparse.Namespace) -> int:
    """P0-1 E1: Ein einzelnes Tool deterministisch ausführen (ohne LLM-Loop).

    Konservative Defaults (Threat-Model E1):
        - SAFE-Tools (read-only): immer erlaubt, ohne Flag.
        - MUTATING/NETWORK-Tools:
            * --dry-run → nur Vorschau, keine Ausführung (Datei wird nicht angefasst)
            * --yes     → explizite Freigabe, Tool wird ausgeführt
            * --no      → explizite Ablehnung, Tool wird NICHT ausgeführt
            * kein Flag + non-interactive TTY → BLOCKED (Approval Pflicht)
    """
    import asyncio

    from core.tools.approval import ApprovalPolicy
    from core.tools.registry import execute_tool, get_tool_schemas

    try:
        tool_args = _parse_tool_args(args.arg)
    except ValueError as exc:
        _emit_error(args, 2, str(exc), "--arg expects key=value pairs")
        return 2

    # Schema-Prüfung: Tool existiert + Parameter-Name korrekt
    schemas = {s.get("function", {}).get("name"): s for s in get_tool_schemas()}
    if args.tool_name not in schemas:
        _emit_error(
            args, 1,
            f"Unbekanntes Tool: '{args.tool_name}'",
            "Verfügbare Tools: " + ", ".join(sorted(schemas.keys())),
        )
        return 1

    # Konservative Policy aus CLI-Flags aufbauen.
    # --yes/--no sind einander widersprüchlich → argparse-Mutual-Exclusion
    # (parse-time) ist die Schranke; hier nur die Policy ableiten.
    policy = ApprovalPolicy(
        auto_approve=args.yes,
        dry_run=args.dry_run,
        interactive=False,  # CLI-Modus: --yes oder --dry-run sind die expliziten Hebel
        declined=args.no,
    )

    try:
        result = asyncio.run(execute_tool(args.tool_name, tool_args, policy=policy))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _emit_error(args, 1, str(exc) or "Tool-Fehler", "Tool-Argumente prüfen")
        return 1

    if args.json:
        print(json.dumps({"tool": args.tool_name, "result": result}, ensure_ascii=False))
    else:
        print(result)

    # Exit-Code-Vertrag:
    #   0 = ausgeführt, dry-run-Vorschau oder SAFE-Auto-Approval
    #   1 = durch Approval-Policy blockiert (mutating, kein --yes / --no / non-interactive)
    if result.startswith("[Abgelehnt]"):
        return 1
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """OpenAI-kompatible Engine starten (/v1/chat/completions)."""
    import uvicorn  # lazy import — hält Startup-Budget klein

    from server.openai import create_openai_app

    token = args.token
    if args.lan and not token:
        token = secrets.token_urlsafe(16)
    host = "0.0.0.0" if args.lan else args.host

    app = create_openai_app(api_token=token or None)
    print(f"  ─────────────────────────────────────")
    print(f"  Engine:  {args.model}")
    print(f"  URL:     http://{host}:{args.port}/v1/chat/completions")
    print(f"  Models:  http://{host}:{args.port}/v1/models")
    if token:
        print(f"  Auth:    X-Auth-Token: {token}")
    else:
        print(f"  Auth:    none (localhost only — use --lan to require a token)")
    print(f"  Docs:    http://{host}:{args.port}/api/docs")
    print(f"  ─────────────────────────────────────\n")

    uvicorn.run(app, host=host, port=args.port, log_level="info")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="miminox",
        description="MiMi Nox local assistant CLI",
        epilog=(
            "Examples:\n"
            "  miminox start                     Start the local web app (default port 8765)\n"
            "  miminox start --lan --open        Expose on LAN for QR mobile pairing, open browser\n"
            "  miminox doctor --fix              Check setup and repair safe local drift\n"
            "  miminox update                    Pull latest, reinstall deps, update model\n"
            "  miminox tui --model gemma4:12b    Start the terminal UI\n"
            "  miminox serve                      Run OpenAI-compatible engine (/v1/chat/completions)\n"
            "  miminox serve --lan                Expose engine on LAN with a generated auth token\n\n"
            "Exit codes:\n"
            "  0  success\n"
            "  1  runtime/repair failure\n"
            "  2  usage error (unknown flag or subcommand)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mimi-nox {MIMI_NOX_VERSION}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser(
        "start",
        help="Start the local web app",
        description="Start the local PWA (offline-first by default; optional --lan for QR mobile pairing).",
    )
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=DEFAULT_PORT)
    start.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    start.add_argument("--lan", action="store_true", help="Expose on the local network for QR mobile pairing")
    start.add_argument("--reload", action="store_true")
    start.add_argument("--open", action="store_true", help="Open the browser after startup")
    start.add_argument("--skip-model-check", action="store_true", help="Start without Ollama/model preflight")
    start.set_defaults(func=cmd_start)

    doctor = sub.add_parser(
        "doctor",
        help="Check local setup",
        description="Diagnose the local setup. --fix repairs safe drift (fast-forward, deps, Ollama).",
    )
    doctor.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    doctor.add_argument("--port", type=int, default=DEFAULT_PORT)
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--fix", action="store_true", help="Repair safe local drift: repo fast-forward, dependencies, Ollama service and model")
    doctor.set_defaults(func=cmd_doctor)

    update = sub.add_parser("update", help="Update repo, dependencies and local model")
    update.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    update.add_argument("--json", action="store_true", help="Machine-readable output")
    update.set_defaults(func=cmd_update)

    tui = sub.add_parser("tui", help="Start the terminal UI")
    tui.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    tui.add_argument(
        "--api-url",
        default=os.environ.get("MIMINOX_API_URL"),
        help="OpenAI-compatible engine base URL (e.g. DGX-Spark ds4 "
        "http://spark-...:8000/v1). Default: local Ollama.",
    )
    tui.add_argument(
        "--configure",
        action="store_true",
        help="Force engine selection even if a config already exists",
    )
    tui.add_argument("--reset", action="store_true")
    # P0-1 E1: Approval-Flags (werden von cmd_tui an die TUI weitergereicht)
    tui.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only; mutating tools are NOT executed (Approval-Gate)",
    )
    yes_no = tui.add_mutually_exclusive_group()
    yes_no.add_argument(
        "--yes",
        action="store_true",
        help="Explicitly approve execution of MUTATING/NETWORK tools",
    )
    yes_no.add_argument(
        "--no",
        action="store_true",
        help="Explicitly decline; MUTATING/NETWORK tools are NOT executed",
    )
    tui.set_defaults(func=cmd_tui)

    completion = sub.add_parser(
        "completion",
        help="Generate shell completions (bash | zsh | fish)",
    )
    completion.add_argument("shell", nargs="?", choices=_COMPLETION_SHELLS)
    completion.set_defaults(func=cmd_completion)

    session = sub.add_parser(
        "session",
        help="Multi-Session-Verwaltung (list / new / switch / rm / rename)",
    )
    session.add_argument(
        "session_action",
        choices=["list", "new", "switch", "rm", "rename"],
        help="Aktion: list (alle anzeigen), new (erzeugen), switch (aktiv machen), rm (löschen), rename (umbenennen)",
    )
    session.add_argument(
        "--id",
        default=None,
        metavar="ID",
        help="Session-ID (für switch / rm / rename)",
    )
    session.add_argument(
        "--title",
        default=None,
        metavar="TITEL",
        help="Titel (für new) bzw. neuer Titel (für rename)",
    )
    session.add_argument("--json", action="store_true", help="Machine-readable JSON")
    session.set_defaults(func=cmd_session)

    serve = sub.add_parser(
        "serve",
        help="Run the OpenAI-compatible engine (/v1/chat/completions)",
    )
    serve.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost)")
    serve.add_argument("--port", type=int, default=8766, help="Port (default: 8766)")
    serve.add_argument("--lan", action="store_true", help="Expose on LAN with a generated auth token")
    serve.add_argument("--token", default=os.environ.get("MIMI_NOX_SERVE_TOKEN", ""), help="Require this X-Auth-Token for every request")
    serve.add_argument(
        "--model",
        default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL),
        help="Model id hint; if unset, the Model Router picks the best tier automatically",
    )
    serve.set_defaults(func=cmd_serve)

    # ── P0-1 E1: Deterministischer Tool-Modus ──────────────────────────────
    tool = sub.add_parser(
        "tool",
        help="Execute a single tool with approval-gates (P0-1 E1: diff / --dry-run / --yes / --no)",
        description=(
            "Execute one tool deterministically (no LLM loop).\n"
            "Approval-gates (conservative defaults, Threat-Model E1):\n"
            "  SAFE tools (read-only)    → always allowed\n"
            "  MUTATING / NETWORK tools → require --yes or --dry-run\n\n"
            "Flags:\n"
            "  --dry-run  Show what WOULD happen; file is NOT touched\n"
            "  --yes      Explicitly approve and execute\n"
            "  --no       Explicitly decline (tool is NOT executed)\n"
            "  --arg K=V  Tool argument (repeatable, JSON-parsed)\n"
            "  --json     Machine-readable output\n\n"
            "Exit codes: 0 = executed / dry-run shown, 3 = blocked by policy, 2 = usage error"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    tool.add_argument("tool_name", help="Tool name (see `miminox tool --help` for the list)")
    tool.add_argument(
        "--arg",
        action="append",
        dest="arg",
        default=[],
        metavar="KEY=VALUE",
        help="Tool argument (repeatable, value JSON-parsed if possible)",
    )
    tool.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only; the tool is NOT executed and no file is touched",
    )
    yes_no = tool.add_mutually_exclusive_group()
    yes_no.add_argument(
        "--yes",
        action="store_true",
        help="Explicitly approve execution of a MUTATING/NETWORK tool",
    )
    yes_no.add_argument(
        "--no",
        action="store_true",
        help="Explicitly decline; the tool is NOT executed",
    )
    tool.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    tool.set_defaults(func=cmd_tool)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.func(args))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _emit_error(args, 1, str(exc) or "Unerwarteter Fehler", "Letzte Ausgabe prüfen und erneut versuchen")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
