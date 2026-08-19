"""MiMi Nox – Channel-Layer (Sprint 3 Gateway-Alpha).

Security-first-Komponenten für den Telegram-Channel als On-Device-Gateway
(Sprint3-G2 Channel-Threat-Model, docs/SECURITY_THREAT_MODEL.md §6):

- ``injection_guard``   — Prompt-Injection-Policy: Channel-Inhalt = Daten,
                          NIE Instruktion (E2).

Pairing (stat. Allowlist, Default-Empty) und Bot-Token-Vault (Keyring/0600)
sind die geprüfte Implementierung in ``core.tg_pairing`` / ``core.tg_tokens``
(Sprint3-G1, e2e-verifiziert). Regel (AGENTS.md / CTO-Pin 3): konservativ —
Channel-Nachrichten laufen durch dieselbe Engine-/Chat-Pipeline wie die PWA.
"""
