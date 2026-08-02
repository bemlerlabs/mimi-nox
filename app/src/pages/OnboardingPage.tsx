import { useState } from 'react'
import { CheckCircle, Loader2, ArrowRight, AlertCircle, Download } from 'lucide-react'

type Step = 'ollama-check' | 'model-pull' | 'welcome'

interface OllamaStatus {
  healthy: boolean
  version?: string
  endpoint: string
}

interface PullProgress {
  model_id: string
  status: string
  percentage?: number
  total?: string
  completed?: string
}

declare global {
  interface Window {
    __TAURI__?: {
      core: {
        invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>
      }
      updater: {
        check: () => Promise<unknown>
      }
    }
  }
}

function invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
  // Tauri 2.x IPC
  if (window.__TAURI__?.core?.invoke) {
    return window.__TAURI__.core.invoke(cmd, args)
  }
  // Fallback for dev
  console.log(`[Tauri IPC] ${cmd}`, args)
  return Promise.resolve({ healthy: false, status: 'dev-mode' })
}

// Custom title bar component (frameless window)
function TitleBar({ onMinimize, onMaximize, onClose }: {
  onMinimize: () => void
  onMaximize: () => void
  onClose: () => void
}) {
  return (
    <div
      className="select-none bg-black/60 backdrop-blur-xl border-b border-white/10 flex items-center px-4 h-12"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex gap-2 ml-auto" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <button
          onClick={onMinimize}
          className="w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-400 transition-colors"
          title="Minimize"
        />
        <button
          onClick={onMaximize}
          className="w-3 h-3 rounded-full bg-green-500 hover:bg-green-400 transition-colors"
          title="Maximize"
        />
        <button
          onClick={onClose}
          className="w-3 h-3 rounded-full bg-red-500 hover:bg-red-400 transition-colors"
          title="Close"
        />
      </div>
    </div>
  )
}

export default function Onboarding() {
  const [step, setStep] = useState<Step>('ollama-check')
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null)
  const [ollamaLoading, setOllamaLoading] = useState(false)
  const [pullProgress, setPullProgress] = useState<PullProgress | null>(null)
  const [pullLoading, setPullLoading] = useState(false)
  const [error, setError] = useState<string>('')

  // Ollama check handler
  const handleCheckOllama = async () => {
    setOllamaLoading(true)
    setError('')
    try {
      const result = await invoke('check_ollama')
      if (result && typeof result === 'object' && 'healthy' in result) {
        setOllamaStatus(result as OllamaStatus)
        // Auto-advance if healthy
        if ((result as OllamaStatus).healthy) {
          setTimeout(() => setStep('model-pull'), 800)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check failed')
    } finally {
      setOllamaLoading(false)
    }
  }

  // Model pull handler
  const handlePullModel = async () => {
    setPullLoading(true)
    setError('')
    setPullProgress(null)
    try {
      const modelId = 'miminox:latest'
      const result = await invoke('pull_model', { model_id: modelId })
      if (result && typeof result === 'object') {
        setPullProgress(result as PullProgress)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pull failed')
      setPullLoading(false)
    }
  }

  // Finish onboarding
  const handleComplete = async () => {
    try {
      await invoke('navigate', { path: '/chat' })
    } catch {
      // Dev mode — just log
      console.log('[Onboarding] Complete → /chat')
    }
  }

  // Window controls
  const handleMinimize = async () => {
    await invoke('minimize_window')
  }
  const handleMaximize = async () => {
    await invoke('maximize_window')
  }
  const handleClose = async () => {
    await invoke('close_window')
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f] text-white overflow-hidden">
      {/* Custom Title Bar */}
      <TitleBar onMinimize={handleMinimize} onMaximize={handleMaximize} onClose={handleClose} />

      {/* Progress Steps Indicator */}
      <div className="flex items-center justify-center gap-2 py-6">
        {(['ollama-check', 'model-pull', 'welcome'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                step === s
                  ? 'bg-violet-600 text-white scale-110'
                  : ['ollama-check', 'model-pull', 'welcome'].indexOf(step) > ['ollama-check', 'model-pull', 'welcome'].indexOf(s)
                    ? 'bg-violet-600/40 text-violet-300'
                    : 'bg-white/10 text-white/40'
              }`}
            >
              {['ollama-check', 'model-pull', 'welcome'].indexOf(step) > ['ollama-check', 'model-pull', 'welcome'].indexOf(s) ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                i + 1
              )}
            </div>
            <span className={`text-xs transition-colors ${step === s ? 'text-violet-300' : 'text-white/30'}`}>
              {i === 0 ? 'Ollama' : i === 1 ? 'Model' : 'Ready'}
            </span>
            {i < 2 && (
              <div className={`w-12 h-0.5 mx-2 rounded transition-colors ${
                ['ollama-check', 'model-pull', 'welcome'].indexOf(step) > i
                  ? 'bg-violet-600'
                  : 'bg-white/10'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="flex-1 flex items-center justify-center px-8">
        <div className="max-w-md w-full">
          {/* Step 1: Ollama Check */}
          {step === 'ollama-check' && (
            <div className="text-center space-y-6">
              <div className="text-6xl">🦙</div>
              <h2 className="text-2xl font-bold">
                Ollama entdecken
              </h2>
              <p className="text-white/60 text-sm">
                MiMi Nox benötigt Ollama für lokale KI-Modelle.
                Wir prüfen, ob es installiert und läuft.
              </p>
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}
              {ollamaStatus && (
                <div className="bg-white/5 rounded-lg p-4 space-y-2 text-left">
                  <div className="flex items-center gap-2">
                    {ollamaStatus.healthy ? (
                      <CheckCircle className="w-5 h-5 text-green-400" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-400" />
                    )}
                    <span className={ollamaStatus.healthy ? 'text-green-400' : 'text-amber-400'}>
                      {ollamaStatus.healthy ? 'Ollama läuft!' : 'Ollama nicht gefunden'}
                    </span>
                  </div>
                  {ollamaStatus.version && (
                    <p className="text-xs text-white/50">Version: {ollamaStatus.version}</p>
                  )}
                  <p className="text-xs text-white/30">Endpoint: {ollamaStatus.endpoint}</p>
                </div>
              )}
              <button
                onClick={handleCheckOllama}
                disabled={ollamaLoading}
                className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg py-3 px-4 font-medium flex items-center justify-center gap-2 transition-all"
              >
                {ollamaLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <ArrowRight className="w-5 h-5" />
                )}
                Ollama prüfen
              </button>
              <p className="text-xs text-white/30">
                Noch nicht installiert?{' '}
                <a
                  href="https://ollama.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-violet-400 hover:underline"
                >
                  ollama.com
                </a>
              </p>
            </div>
          )}

          {/* Step 2: Model Pull */}
          {step === 'model-pull' && (
            <div className="text-center space-y-6">
              <div className="text-6xl">🤖</div>
              <h2 className="text-2xl font-bold">
                Modell herunterladen
              </h2>
              <p className="text-white/60 text-sm">
                Lade das Miminox-Modell herunter.
                Die erste Installation kann einige Minuten dauern.
              </p>
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}
              {pullProgress && (
                <div className="bg-white/5 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-white/70">{pullProgress.model_id}</span>
                    <span className="text-violet-400">{pullProgress.percentage}%</span>
                  </div>
                  <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-violet-500 to-purple-400 h-full rounded-full transition-all duration-300"
                      style={{ width: `${pullProgress.percentage || 0}%` }}
                    />
                  </div>
                  <p className="text-xs text-white/40">{pullProgress.status}</p>
                </div>
              )}
              <button
                onClick={handlePullModel}
                disabled={pullLoading}
                className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg py-3 px-4 font-medium flex items-center justify-center gap-2 transition-all"
              >
                {pullLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Download className="w-5 h-5" />
                )}
                {pullProgress ? 'Erneut herunterladen' : 'Miminox herunterladen'}
              </button>
            </div>
          )}

          {/* Step 3: Welcome */}
          {step === 'welcome' && (
            <div className="text-center space-y-6">
              <div className="text-7xl">✨</div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-purple-300 bg-clip-text text-transparent">
                Willkommen bei MiMi Nox
              </h2>
              <p className="text-white/60 text-sm max-w-xs mx-auto">
                Dein lokaler KI-Assistent. Privat. Sicher. Immer verfügbar.
              </p>
              <div className="bg-white/5 rounded-lg p-4 space-y-2 text-left text-sm">
                <div className="flex items-center gap-2 text-white/70">
                  <CheckCircle className="w-4 h-4 text-violet-400 shrink-0" />
                  <span>Ollama verbunden</span>
                </div>
                <div className="flex items-center gap-2 text-white/70">
                  <CheckCircle className="w-4 h-4 text-violet-400 shrink-0" />
                  <span>Modell bereit</span>
                </div>
                <div className="flex items-center gap-2 text-white/70">
                  <CheckCircle className="w-4 h-4 text-violet-400 shrink-0" />
                  <span>Lokale Verarbeitung</span>
                </div>
                <div className="flex items-center gap-2 text-white/70">
                  <CheckCircle className="w-4 h-4 text-violet-400 shrink-0" />
                  <span>Keine Cloud nötig</span>
                </div>
              </div>
              <button
                onClick={handleComplete}
                className="w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white rounded-lg py-3 px-4 font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-violet-500/20"
              >
                <ArrowRight className="w-5 h-5" />
                MiMi Nox starten
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-3 text-xs text-white/20">
        MiMi Nox v1.0.0 — Local AI Assistant
      </div>
    </div>
  )
}