"""MiMi Nox – leichtgewichtiger MCP-Client (Model Context Protocol).

Bindet externe MCP-Server als Tools an die Tool-Registry an, ohne die schwere
`mcp`-SDK-Abhängigkeit: wir sprechen das standardisierte JSON-RPC 2.0-Protokoll
(streamable HTTP transport) direkt mit `httpx`, und stdio-Server über subprocess.

Transporte:
- http  : POST JSON-RPC an einen HTTP-Endpunkt (streamable HTTP / SSE)
- stdio : Startet einen lokalen MCP-Server als subprocess, JSON-RPC über stdin/stdout

Der Client ist bewusst minimal und fehlertolerant: bei Netz/Timeout-Fehlern wird
kein Abbruch, sondern ein lesbarer Fehlerstring zurückgegeben, damit der Agent
weiterarbeiten kann. Alle Funktionen sind async, da der MCP-Standard async ist.
"""
from __future__ import annotations

import asyncio
import json
import shlex
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

# httpx wird lazy importiert (nur im http-Pfad) — kein Import-Fehler, wenn es fehlt.
try:
    import httpx
except Exception:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore[assignment]

_MCP_PROTOCOL_VERSION = "2024-11-05"
_MCP_NAMESPACE = "mcp_"
# Server-Specs (transport:endpoint). Env: MIMI_NOX_MCP_SERVERS="http://…/mcp,stdio:npx …"
_MCP_SERVERS: list[MCPServerSpec] = []
# Registrierte Remote-Tools: {tool_name: {"server", "tool", "call", "schema"}}
_MCP_TOOLS: dict[str, dict[str, Any]] = {}
_MCP_COUNTER: dict[str, int] = {}


@dataclass
class MCPServerSpec:
    transport: str
    endpoint: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    label: str = ""

    def render(self) -> str:
        if self.transport == "stdio":
            return f"stdio:{shlex.join([self.command, *self.args])}"
        return self.endpoint

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MCPServerSpec):
            return NotImplemented
        return (
            self.transport == other.transport
            and self.endpoint == other.endpoint
            and self.command == other.command
            and self.args == other.args
        )


def parse_server_spec(spec: str) -> MCPServerSpec:
    """Parse "stdio:cmd arg…" oder "http://host:port[/mcp]" in eine ServerSpec."""
    spec = spec.strip()
    if spec.startswith("stdio:"):
        rest = spec[len("stdio:"):].strip()
        parts = shlex.split(rest)
        cmd = parts[0] if parts else ""
        return MCPServerSpec(transport="stdio", command=cmd, args=parts[1:])
    endpoint = spec if spec.startswith("http") else f"http://{spec}"
    return MCPServerSpec(transport="http", endpoint=endpoint)


def set_mcp_servers(specs: list[str]) -> list[MCPServerSpec]:
    """Setzt die aktiven MCP-Server (aus Kommandozeile/Env). Leert die Registry."""
    global _MCP_SERVERS
    unregister_mcp_tools()
    _MCP_SERVERS = [parse_server_spec(s) for s in specs if s.strip()]
    return _MCP_SERVERS


def get_mcp_servers() -> list[MCPServerSpec]:
    return list(_MCP_SERVERS)


def get_mcp_tools() -> dict[str, dict[str, Any]]:
    """Nur die Remote-Tools, nicht die eingebauten — getrennte Namespace."""
    return dict(_MCP_TOOLS)


def _invalidate_schema_cache() -> None:
    """Lazy Import vermeidet Zirkularität (registry importiert mcp_client)."""
    from core.tools.registry import invalidate_tool_schema_cache
    invalidate_tool_schema_cache()


def register_mcp_tool(name: str, server: str, tool: str, call: Callable, schema: dict) -> dict:
    """Registriert ein Remote-Tool in der MCP-Namespace. Kollision mit Builtins → ValueError."""
    if name in _MCP_TOOLS:
        raise ValueError(f"MCP-Tool {name} bereits registriert")
    _MCP_TOOLS[name] = {"server": server, "tool": tool, "call": call, "schema": schema}
    _invalidate_schema_cache()
    return _MCP_TOOLS[name]


def unregister_mcp_tools() -> None:
    _MCP_TOOLS.clear()
    _invalidate_schema_cache()


def _mcp_id() -> int:
    _MCP_COUNTER["n"] = _MCP_COUNTER.get("n", 0) + 1
    return _MCP_COUNTER["n"]


def _rpc(method: str, params: dict[str, Any], request_id: int) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


def _result_text(content: list[dict]) -> str:
    return "\n".join(str(c.get("text", "")) for c in content if c.get("type") == "text")


class MCPClient:
    """Ein einzelner MCP-Server: list_tools() → Tools, call_tool() → Ergebnis."""

    def __init__(self, endpoint: str, transport: str = "http", label: str = "", timeout: float = 30.0):
        self.endpoint = endpoint
        self.transport = transport
        self.label = label or endpoint
        self.timeout = timeout
        self.session_id: str | None = None
        self._proc: Any | None = None

    # --- JSON-RPC Payload-Builder (rein, testbar) ---
    def _build_initialize(self) -> dict:
        return _rpc("initialize", {"protocolVersion": _MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "mimi-nox", "version": "2.0.0"}}, _mcp_id())

    def _build_tools_list(self, request_id: int) -> dict:
        return _rpc("tools/list", {}, request_id)

    def _build_tools_call(self, name: str, arguments: dict, request_id: int) -> dict:
        return _rpc("tools/call", {"name": name, "arguments": arguments}, request_id)

    # --- Response-Parser (rein, testbar) ---
    def _parse_tools_response(self, resp: dict) -> list[dict]:
        if "error" in resp:
            return []
        return resp.get("result", {}).get("tools", []) or []

    def _extract_tool_result(self, resp: dict) -> tuple[str, bool]:
        result = resp.get("result", {})
        is_error = bool(result.get("isError"))
        return _result_text(result.get("content", [])), is_error

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": _MCP_PROTOCOL_VERSION,
            "MCP-Session-Id": self.session_id or "",
        }

    # --- Transport ---
    async def _post(self, endpoint: str, headers: dict, body: dict) -> dict:
        """HTTP POST mit JSON-RPC. Überschreibbar für Tests."""
        if httpx is None:  # pragma: no cover
            return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": "httpx not installed"}}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(endpoint, headers=headers, json=body)
            try:
                return resp.json()
            except Exception:
                return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32003, "message": f"non-JSON reply ({resp.status_code})"}}

    async def _send(self, body: dict) -> dict:
        if self.transport == "stdio":
            return await self._stdio_send(body)
        return await self._post(self.endpoint, self._headers(), body)

    async def _stdio_send(self, body: dict) -> dict:
        """Startet den Server lazy und schreibt/liest eine JSON-Zeile über stdio."""
        if self._proc is None:
            if not self.endpoint:
                return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": "stdio server not configured"}}
            self._proc = await asyncio.create_subprocess_exec(
                self.endpoint,  # command
                *[],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        if self._proc.stdin is None or self._proc.stdout is None:
            return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": "stdio pipe closed"}}
        self._proc.stdin.write((json.dumps(body) + "\n").encode())
        await self._proc.stdin.drain()
        try:
            line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=self.timeout)
        except asyncio.TimeoutError:
            return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32002, "message": "stdio timeout"}}
        if not line:
            return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32001, "message": "stdio server closed"}}
        try:
            return json.loads(line.decode().strip())
        except Exception:
            return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32003, "message": "non-JSON stdio reply"}}

    # --- Public API ---
    async def list_tools(self) -> list[dict]:
        """Listet Remote-Tools. Fehlertolerant: Fehler → []. Session wird nicht initialisiert
        (viele Server antworten auf tools/list ohne initialize); bei Bedarf via initialize()."""
        try:
            resp = await self._send(self._build_tools_list(_mcp_id()))
        except Exception as exc:
            return [{"error": f"mcp list failed: {exc!r}"}]
        tools = self._parse_tools_response(resp)
        if tools:
            return tools
        return []

    async def initialize(self) -> dict:
        return await self._send(self._build_initialize())

    async def call_tool(self, name: str, arguments: dict | None = None) -> tuple[str, bool]:
        """Ruft ein Remote-Tool auf. Gibt (text, is_error) zurück, nie einen Abbruch."""
        arguments = arguments or {}
        try:
            resp = await self._send(self._build_tools_call(name, arguments, _mcp_id()))
        except Exception as exc:
            return f"mcp call failed: {exc!r}", True
        return self._extract_tool_result(resp)

    async def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.stdin.close() if self._proc.stdin else None
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


async def sync_mcp_tools(server_specs: list[MCPServerSpec] | None = None) -> list[str]:
    """Verbindet alle konfigurierten MCP-Server, listet deren Tools und registriert sie
    in der MCP-Namespace. Rückgabe: Liste der neu registrierten Tool-Namen."""
    specs = server_specs if server_specs is not None else _MCP_SERVERS
    unregister_mcp_tools()
    registered: list[str] = []
    for idx, spec in enumerate(specs):
        endpoint = spec.endpoint if spec.transport == "http" else spec.command
        client = MCPClient(endpoint=endpoint, transport=spec.transport, label=spec.label or f"mcp-{idx}")
        try:
            tools = await client.list_tools()
            for tool in tools:
                if "error" in tool:
                    continue
                name = tool.get("name")
                if not name:
                    continue
                safe = name.replace(" ", "_").replace("-", "_")
                full = f"{_MCP_NAMESPACE}{safe}"

                async def _call(arguments: dict | None = None, _client=client, _name=name) -> tuple[str, bool]:
                    return await _client.call_tool(_name, arguments or {})

                register_mcp_tool(full, spec.label or endpoint, name, _call, {"name": full, "description": tool.get("description", ""), "inputSchema": tool.get("inputSchema", {})})
                registered.append(full)
        finally:
            # Server bleibt für call_tool offen; nur bei HTTP ist kein persistent state nötig.
            if spec.transport == "stdio":
                await client.close()
    return registered


def mcp_tool_names() -> list[str]:
    return sorted(_MCP_TOOLS.keys())


async def call_registered_mcp_tool(name: str, arguments: dict | None = None) -> tuple[str, bool]:
    """Dispatch auf ein registriertes Remote-Tool (Name wie 'mcp_filesystem_read_text')."""
    entry = _MCP_TOOLS.get(name)
    if entry is None:
        return f"unknown MCP tool {name}", True
    call: Callable = entry["call"]
    return await call(arguments or {})
