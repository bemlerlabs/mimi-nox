"""Command line helper for the MiMi Nox local web app."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


DEFAULT_MODEL = "gemma4:12b"
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
    checks.append(("Project files", (PROJECT_ROOT / "app" / "src" / "index.html").exists(), str(PROJECT_ROOT)))
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
    if (PROJECT_ROOT / ".git").exists():
        _run(["git", "pull", "--ff-only"])

    installer = PROJECT_ROOT / "install.sh"
    if not installer.exists():
        print("install.sh not found", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["OLLAMA_HOST"] = LOCAL_OLLAMA_HOST
    env["MIMI_NOX_MODEL"] = args.model
    env["MIMI_NOX_NO_START"] = "1"
    return _run(["bash", str(installer), "--no-start"], env=env).returncode


def cmd_tui(args: argparse.Namespace) -> int:
    import clawdash

    forwarded = ["mimi-nox"]
    if args.model:
        forwarded.extend(["--model", args.model])
    if args.reset:
        forwarded.append("--reset")
    old_argv = sys.argv
    try:
        sys.argv = forwarded
        clawdash.main()
    finally:
        sys.argv = old_argv
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="miminox", description="MiMi Nox local assistant CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start the local web app")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=DEFAULT_PORT)
    start.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    start.add_argument("--lan", action="store_true", help="Expose on the local network for QR mobile pairing")
    start.add_argument("--reload", action="store_true")
    start.add_argument("--open", action="store_true", help="Open the browser after startup")
    start.add_argument("--skip-model-check", action="store_true", help="Start without Ollama/model preflight")
    start.set_defaults(func=cmd_start)

    doctor = sub.add_parser("doctor", help="Check local setup")
    doctor.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    doctor.add_argument("--port", type=int, default=DEFAULT_PORT)
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--fix", action="store_true", help="Repair safe local drift: repo fast-forward, dependencies, Ollama service and model")
    doctor.set_defaults(func=cmd_doctor)

    update = sub.add_parser("update", help="Update repo, dependencies and local model")
    update.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    update.set_defaults(func=cmd_update)

    tui = sub.add_parser("tui", help="Start the terminal UI")
    tui.add_argument("--model", default=os.environ.get("MIMI_NOX_MODEL", DEFAULT_MODEL))
    tui.add_argument("--reset", action="store_true")
    tui.set_defaults(func=cmd_tui)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
