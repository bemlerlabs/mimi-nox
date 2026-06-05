param(
  [string]$InstallDir = "$HOME\Documents\MiMi-Nox",
  [string]$Model = "gemma4:12b",
  [int]$Port = 8765,
  [switch]$NoStart,
  [switch]$SkipModel
)

$ErrorActionPreference = "Stop"
$RepoUrl = $env:MIMI_NOX_REPO_URL
if (-not $RepoUrl) { $RepoUrl = "https://github.com/MimiTechAi/mimi-nox.git" }

function Step($Text) { Write-Host "`n> $Text" -ForegroundColor Green }
function Ok($Text) { Write-Host "  OK $Text" -ForegroundColor Green }
function Fail($Text) { Write-Error $Text; exit 1 }

Write-Host ""
Write-Host "MiMi Nox offline-first installer" -ForegroundColor Green
Write-Host "Local Ollama + $Model by default. Online/API is optional." -ForegroundColor DarkGray

if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "app\src\index.html")) {
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
  & powershell -ExecutionPolicy Bypass -File ".\install.ps1" -InstallDir $InstallDir -Model $Model -Port $Port -NoStart:$NoStart -SkipModel:$SkipModel
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

Step "Check Ollama"
$Ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $Ollama) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
    $Ollama = Get-Command ollama -ErrorAction SilentlyContinue
  } else {
    Fail "Ollama CLI is missing. Install Ollama from https://ollama.com/download and run this script again."
  }
}
Ok $Ollama.Source

Step "Start Ollama service"
try {
  Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
} catch {
  Start-Process -FilePath $Ollama.Source -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 4
}
try {
  Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 | Out-Null
} catch {
  Fail "Ollama service is not responding."
}
Ok "Ollama running"

if (-not $SkipModel) {
  Step "Install AI model: $Model"
  & $Ollama.Source show $Model *> $null
  if ($LASTEXITCODE -eq 0) {
    Ok "$Model already installed"
  } else {
    Write-Host "  Gemma 4 12B: 16GB RAM/unified memory recommended, 256K context. Restarting resumes the download." -ForegroundColor DarkGray
    & $Ollama.Source pull $Model
  }

  Step "Install memory model: nomic-embed-text"
  & $Ollama.Source show "nomic-embed-text" *> $null
  if ($LASTEXITCODE -ne 0) {
    & $Ollama.Source pull "nomic-embed-text"
  }
  Ok "Models ready"
}

Step "Set up Python environment"
if (-not (Test-Path ".venv")) {
  & $Python.Source -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -e ".[gui,voice]"
Ok "Dependencies installed"

Step "Create local data folders"
New-Item -ItemType Directory -Force -Path "$HOME\.mimi-nox\memory", "$HOME\.mimi-nox\skills", "$HOME\.mimi-nox\sessions\audio", "$HOME\.mimi-nox\sessions\images" | Out-Null
Ok "$HOME\.mimi-nox ready"

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Start: .\.venv\Scripts\miminox.exe start --open"
Write-Host "Check: .\.venv\Scripts\miminox.exe doctor"
Write-Host "URL:   http://127.0.0.1:$Port"

if (-not $NoStart) {
  & ".\.venv\Scripts\miminox.exe" start --port $Port --model $Model --open
}
