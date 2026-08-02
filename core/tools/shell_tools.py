"""MiMi Nox – run_shell / execute_confirmed_shell tools."""

from __future__ import annotations

import asyncio
import subprocess

from core.tools.base import (
    ALLOWED_COMMANDS,
    BLOCKED_PATTERNS,
    SHELL_TIMEOUT_SECONDS,
    ShellConfirmationRequired,
    ShellTimeoutError,
)


async def run_shell(command: str) -> str:
    raise ShellConfirmationRequired(command)


async def execute_confirmed_shell(command: str, confirmed: bool) -> str:
    if not confirmed:
        return "Abgebrochen."

    cmd_name = command.strip().split()[0] if command.strip() else ""
    if cmd_name not in ALLOWED_COMMANDS:
        return f"⚠️ Sicherheit: Befehl '{cmd_name}' ist nicht in der Whitelist ({len(ALLOWED_COMMANDS)} erlaubte Befehle)."

    cmd_lower = command.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            return f"⚠️ Sicherheit: Befehl enthält gesperrtes Muster '{pattern}'."

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            final_out = f"{output}\n[exit {result.returncode}] {error}".strip()
        else:
            final_out = output or "(kein Output)"

        if len(final_out) > 10000:
            final_out = final_out[:10000] + "\n\n... [Shell-Output sicherheitshalber auf 10.000 Zeichen gekürzt]"

        return final_out

    except subprocess.TimeoutExpired:
        raise ShellTimeoutError(command, SHELL_TIMEOUT_SECONDS)
