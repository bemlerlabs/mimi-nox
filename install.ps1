param(
  [string]$InstallDir = "$HOME\Documents\MiMi-Nox",
  [int]$Port = 8765,
  [switch]$NoStart,
  [switch]$Cli
)

$ErrorActionPreference = "Stop"
$RepoUrl = $env:MIMI_NOX_REPO_URL
if (-not $RepoUrl) { $RepoUrl = "https://github.com/bemlerlabs/mimi-nox.git" }

$OllamaHost = if ($env:MIMI_NOX_OLLAMA_HOST) { $env:MIMI_NOX_OLLAMA_HOST } else { "127.0.0.1:11434" }
$OllamaUrl = if ($OllamaHost -notmatch '^https?://') { "http://$OllamaHost" } else { $OllamaHost }

function Step($Text) { Write-Host "`n> $Text" -ForegroundColor Green }
function Ok($Text) { Write-Host "  OK $Text" -ForegroundColor Green }
function Warn($Text) { Write-Host "  WARN $Text" -ForegroundColor Yellow }
function Fail($Text) { Write-Error $Text; exit 1 }

# Freier Speicherplatz (GB) auf dem Laufwerk, auf dem das Repo liegt.
function Get-FreeSpaceGB {
  try {
    $letter = (Get-Location).Path.Substring(0,1)
    $vol = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$letter:'" -ErrorAction SilentlyContinue
    if ($vol) { return [math]::Floor($vol.FreeSpace / 1GB) }
  } catch { }
  return -1
}

Write-Host ""
Write-Host "MiMi Nox offline-first installer" -ForegroundColor Green
Write-Host "One-command install. AI-Engine wird in der App gewählt (lokale Ollama oder externer Endpunkt)." -ForegroundColor DarkGray

if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "app\src")) {
  Step "Prepare install folder"
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "Git is missing. Install Git for Windows and run this script again."
  }
  $Parent = Split-Path $InstallDir -Parent
  New-Item -ItemType Directory -Force -Path $Parent | Out-Null
  if (Test-Path "$InstallDir\.git") {
    Ok "Existing repository found: $InstallDir"
    Set-Location $InstallDir
    git pull --ff-only
  } elseif (Test-Path $InstallDir) {
    Fail "$InstallDir already exists but is not a Git repository. Choose another -InstallDir."
  } else {
    git clone $RepoUrl $InstallDir
    Set-Location $InstallDir
  }
  & powershell -ExecutionPolicy Bypass -File ".\install.ps1" -InstallDir $InstallDir -Port $Port -NoStart:$NoStart -Cli:$Cli
  exit $LASTEXITCODE
}

Step "Check Python 3.10+"
function Find-Python {
  $Candidate = Get-Command python -ErrorAction SilentlyContinue
  if (-not $Candidate) { $Candidate = Get-Command py -ErrorAction SilentlyContinue }
  if (-not $Candidate) { return $null }
  & $Candidate.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
  if ($LASTEXITCODE -eq 0) { return $Candidate }
  return $null
}

$Python = Find-Python
if (-not $Python) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $Python = Find-Python
  }
}
if (-not $Python) { Fail "Python 3.10+ is missing. Install Python 3.12 and run this script again." }
Ok (& $Python.Source -c "import sys; print(sys.version.split()[0])")

# Speicherplatz: ~4 GB fuer Produkt/Abhaengigkeiten/PWA-Build. Modell-Downloads
# laufen NICHT hier (Engine wird in der App gewählt) -> nur Warnung, kein Abbruch.
Step "Check disk space"
$FreeGB = Get-FreeSpaceGB
if ($FreeGB -ge 0 -and $FreeGB -lt 4) {
  Warn "Weniger als ~4 GB freier Speicher ($FreeGB GB). Installation wird trotzdem versucht."
} else {
  Ok "Disk space OK"
}

# ── KI-Engine (Info-Step, nie blockierend) ───────────────────────────────────
# Mandat 2026-08-21: Ollama wird NICHT installiert, KEINE Modelle geladen.
# Dieser Schritt prueft nur, ob lokal Ollama bereitsteht, und zeigt einen
# Hinweis. Fehlt Ollama -> Warnung (kein Abbruch); die Engine wird in der App
# gewählt (SetupPage: lokale Ollama / remote Ollama / OpenAI-kompatibel).
Step "Check AI engine (info)"
$Ollama = Get-Command ollama -ErrorAction SilentlyContinue
$OllamaServiceOk = $false
if ($Ollama) {
  try {
    Invoke-RestMethod "$OllamaUrl/api/tags" -TimeoutSec 3 | Out-Null
    $OllamaServiceOk = $true
  } catch { }
}
if ($Ollama -and $OllamaServiceOk) {
  Ok "Ollama detected - its models are available for selection in the app."
} else {
  Warn "Kein Ollama erkannt - das ist OK: MiMi Nox installiert keine KI von selbst."
  Write-Host "     Nach dem Start waehlst du in der App deine Engine (lokale Ollama oder externer Endpunkt wie DGX)." -ForegroundColor DarkGray
}

Step "Set up Python environment"
if (-not (Test-Path ".venv")) {
  & $Python.Source -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
if ($Cli) {
  Write-Host "  CLI mode: installing minimal dependencies (tui)"
  & ".\.venv\Scripts\pip.exe" install -e ".[tui]"
} else {
  & ".\.venv\Scripts\pip.exe" install -e ".[gui,voice]"
}
Ok "Dependencies installed"

# ── PWA-Build (Desktop-Modus) ───────────────────────────────────────────────
# Der Server liefert die Web-App (PWA) aus app/dist/ — ein Build-Artefakt,
# das git-ignoriert ist und in einem frischen Clone fehlt. Im Desktop-Modus
# bauen wir das Frontend jetzt, damit http://127.0.0.1:8765/ direkt laedt.
if (-not $Cli) {
  Step "Build PWA (Web-App)"
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "npm fehlt — Node.js ist erforderlich für den PWA-Build. Installiere Node.js (https://nodejs.org) und starte den Installer erneut."
  }
  Push-Location "$PSScriptRoot\app"
  try {
    & npm ci
    & npm run build
    if ($LASTEXITCODE -ne 0) {
      Fail "PWA-Build fehlgeschlagen (npm exit code $LASTEXITCODE)."
    }
    if (-not (Test-Path "dist\index.html")) {
      Fail "PWA-Build fehlgeschlagen: dist\index.html existiert nicht."
    }
    Ok "PWA gebaut → app\dist"
  } finally {
    Pop-Location
  }
} else {
  Write-Host "  CLI mode: PWA build skipped (TUI needs no frontend)" -ForegroundColor DarkGray
}

Step "Create local data folders"
New-Item -ItemType Directory -Force -Path "$HOME\.mimi-nox\memory", "$HOME\.mimi-nox\skills", "$HOME\.mimi-nox\sessions\audio", "$HOME\.mimi-nox\sessions\images" | Out-Null
Ok "$HOME\.mimi-nox ready"

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Check: .\.venv\Scripts\miminox.exe doctor"
if ($Cli) {
  Write-Host "Start: .\.venv\Scripts\miminox.exe tui"
} else {
  Write-Host "Start: .\.venv\Scripts\miminox.exe start --open"
  Write-Host "URL:   http://127.0.0.1:$Port"
}

if (-not $NoStart) {
  if ($Cli) {
    & ".\.venv\Scripts\miminox.exe" tui
  } else {
    & ".\.venv\Scripts\miminox.exe" start --port $Port --open
  }
}
