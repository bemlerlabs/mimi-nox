# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 4.x     | Active |
| < 4.0   | Best-effort only |

## Reporting a Vulnerability

**⚠️ Do NOT open a public GitHub issue for security vulnerabilities.**

Please report security issues responsibly by emailing:

📧 **security@mimiai.de**

Include:
- A description of the vulnerability
- Steps to reproduce
- Your assessment of the severity (Critical / High / Medium / Low)
- Any suggested fix (optional but appreciated)

## Response Timeline

| Phase | Timeframe |
|-------|-----------|
| Acknowledgment | Within **48 hours** |
| Initial assessment | Within **5 business days** |
| Fix release | Within **30 days** (critical: 7 days) |
| Public disclosure | After fix is released |

## Security Measures

MiMi Nox is designed with **privacy and security as core principles**:

- **Zero Telemetry in this repository** — No analytics or tracking pipeline is included
- **Local-First Default** — Default AI inference uses local Ollama; optional providers are opt-in
- **Shell Sandbox** — Commands always require explicit user approval
- **File Whitelist** — Access restricted to safe directories only
- **XSS Protection** — All output sanitized via DOMPurify
- **SVG Sanitizer** — Blocks script injection in generated graphics
- **No API Keys Required for Core Use** — External providers are optional
- **Virtual Environment Isolation** — Python dependencies run from the project environment

## Scope

The following are **in scope** for security reports:

- Remote code execution
- Cross-site scripting (XSS)
- Authentication bypass
- Information disclosure
- Privilege escalation
- Denial of service

The following are **out of scope**:

- Issues in dependencies (report to upstream)
- Attacks requiring physical access to the device
- Social engineering attacks

---

*MiMi Tech AI UG — Bad Liebenzell, Black Forest, Germany 🌲*
