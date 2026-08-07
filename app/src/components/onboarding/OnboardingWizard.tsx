import { useState } from 'react'
import { CheckCircle } from 'lucide-react'
import OllamaCheck, { type OllamaStatus } from './OllamaCheck'
import ModelSelector, { type PullProgress } from './ModelSelector'
import FirstChatSetup from './FirstChatSetup'

type Step = 'ollama-check' | 'model-pull' | 'welcome'

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

const STEPS: Step[] = ['ollama-check', 'model-pull', 'welcome']

function ProgressIndicator({ step }: { step: Step }) {
  const currentIndex = STEPS.indexOf(step)
  return (
    <div className="flex items-center justify-center gap-2 py-6">
      {STEPS.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
              step === s
                ? 'bg-violet-600 text-white scale-110'
                : currentIndex > i
                  ? 'bg-violet-600/40 text-violet-300'
                  : 'bg-white/10 text-white/40'
            }`}
          >
            {currentIndex > i ? <CheckCircle className="w-4 h-4" /> : i + 1}
          </div>
          <span className={`text-xs transition-colors ${step === s ? 'text-violet-300' : 'text-white/30'}`}>
            {i === 0 ? 'Ollama' : i === 1 ? 'Model' : 'Ready'}
          </span>
          {i < 2 && (
            <div
              className={`w-12 h-0.5 mx-2 rounded transition-colors ${
                currentIndex > i ? 'bg-violet-600' : 'bg-white/10'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  )
}

/** Onboarding-Wizard: Ollama-Check → Modell-Pull → Welcome (3-Schritt-Zustandsmaschine) */
export default function OnboardingWizard() {
  const [step, setStep] = useState<Step>('ollama-check')
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null)
  const [ollamaLoading, setOllamaLoading] = useState(false)
  const [pullProgress, setPullProgress] = useState<PullProgress | null>(null)
  const [pullLoading, setPullLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCheckOllama = async () => {
    setOllamaLoading(true)
    setError('')
    try {
      const result = await invoke('check_ollama')
      if (result && typeof result === 'object' && 'healthy' in result) {
        setOllamaStatus(result as OllamaStatus)
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

  const handleComplete = async () => {
    try {
      await invoke('navigate', { path: '/chat' })
    } catch {
      console.log('[Onboarding] Complete → /chat')
    }
  }

  const handleMinimize = async () => { await invoke('minimize_window') }
  const handleMaximize = async () => { await invoke('maximize_window') }
  const handleClose = async () => { await invoke('close_window') }

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f] text-white overflow-hidden">
      <TitleBar onMinimize={handleMinimize} onMaximize={handleMaximize} onClose={handleClose} />
      <ProgressIndicator step={step} />

      <div className="flex-1 flex items-center justify-center px-8">
        <div className="max-w-md w-full">
          {step === 'ollama-check' && (
            <OllamaCheck
              status={ollamaStatus}
              loading={ollamaLoading}
              error={error}
              onCheck={handleCheckOllama}
            />
          )}
          {step === 'model-pull' && (
            <ModelSelector
              progress={pullProgress}
              loading={pullLoading}
              error={error}
              onPull={handlePullModel}
            />
          )}
          {step === 'welcome' && <FirstChatSetup onComplete={handleComplete} />}
        </div>
      </div>

      <div className="text-center py-3 text-xs text-white/20">MiMi Nox v1.0.0 — Local AI Assistant</div>
    </div>
  )
}
