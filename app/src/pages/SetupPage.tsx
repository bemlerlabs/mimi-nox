import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Cpu, Server, PlugZap, Loader2, Check, AlertTriangle } from 'lucide-react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import {
  probeProvider,
  updateSettings,
  resetSetup,
  type ProviderProbeResponse,
} from '@/lib/api'

type ProviderKind = 'local_ollama' | 'custom_ollama' | 'openai_compatible'

/**
 * SetupPage — First-Run-Engine-Auswahl (End-User-Onboarding).
 *
 * Der User wählt nach der Installation selbst seine Engine:
 *  - Ollama lokal (127.0.0.1:11434, wird automatisch erkannt)
 *  - Ollama remote (z. B. DGX/LAN — eigener Endpunkt)
 *  - OpenAI-kompatibel (vLLM/SGLang/… — eigener Endpunkt)
 *
 * MiMi Nox installiert NICHTS und lädt keine Modelle — es wird der
 * Endpunkt per Probe geprüft (Ollama: /api/tags, OpenAI: /v1/models),
 * die erkannten Modelle werden zur Auswahl gelistet und die Choice
 * wird in engine.json persistiert (via POST /api/settings).
 */

const OPTIONS: { kind: ProviderKind; icon: typeof Cpu; testId: string }[] = [
  { kind: 'local_ollama', icon: Cpu, testId: 'setup-option-local' },
  { kind: 'custom_ollama', icon: Server, testId: 'setup-option-custom' },
  { kind: 'openai_compatible', icon: PlugZap, testId: 'setup-option-openai' },
]

interface SetupPageProps {
  /** Wird aufgerufen, wenn die Engine persistiert wurde (Gate re-checkt Status). */
  onDone: () => void
}

export default function SetupPage({ onDone }: SetupPageProps) {
  const { t } = useTranslation()
  const [kind, setKind] = useState<ProviderKind>('local_ollama')
  const [endpoint, setEndpoint] = useState('')
  const [probeState, setProbeState] = useState<ProviderProbeResponse | null>(null)
  const [probing, setProbing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [model, setModel] = useState('')

  const needsUrl = kind !== 'local_ollama'

  async function runProbe(overrideKind?: ProviderKind) {
    const k = overrideKind ?? kind
    setProbing(true)
    setError('')
    setModel('')
    try {
      const baseUrl = k === 'local_ollama' ? '' : endpoint.trim()
      const res = await probeProvider(k, baseUrl || undefined)
      setProbeState(res)
      if (res.reachable) {
        const first = res.models[0]
        if (first) setModel(first)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setProbing(false)
    }
  }

  async function handleFinish() {
    if (!probeState?.reachable || !model) return
    setSaving(true)
    setError('')
    try {
      await updateSettings({
        provider: {
          type: kind,
          model,
          endpoint: needsUrl ? endpoint.trim() : undefined,
        },
      })
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setSaving(false)
    }
  }

  async function handleReset() {
    // Engine-Auswahl vergessen (z. B. nach /chat zurück und neu wählen)
    await resetSetup().catch(() => {})
    window.location.hash = '#/'
    window.location.reload()
  }

  const reachable = probeState?.reachable === true

  return (
    <ErrorBoundary
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#0b1319] text-white/60">
          {t('error.fallback')}
        </div>
      }
    >
      <div className="flex min-h-screen items-center justify-center bg-[#0b1319] px-6 py-12">
        <div className="w-full max-w-md" data-testid="setup-page">
          <div className="mb-8 text-center">
            <div className="mb-3 text-xs uppercase tracking-[0.25em] text-green-400/70">
              {t('setup.kicker')}
            </div>
            <h1 className="text-3xl font-medium text-white">{t('setup.title')}</h1>
            <p className="mt-2 text-sm text-white/40">{t('setup.subtitle')}</p>
          </div>

          {/* Engine-Auswahl */}
          <div className="mb-5 grid gap-2" role="radiogroup" aria-label={t('setup.title')}>
            {OPTIONS.map(({ kind: k, icon: Icon, testId }) => (
              <button
                key={k}
                type="button"
                role="radio"
                aria-checked={kind === k}
                data-testid={testId}
                onClick={() => {
                  setKind(k)
                  setProbeState(null)
                  setError('')
                  if (k === 'local_ollama') void runProbe(k)
                }}
                className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition-colors ${
                  kind === k
                    ? 'border-green-500/50 bg-green-500/10 text-white'
                    : 'border-white/10 bg-white/[0.03] text-white/60 hover:bg-white/[0.06]'
                }`}
              >
                <Icon className="h-4 w-4 flex-shrink-0 text-green-400" />
                <span className="flex-1">{t(`setup.option.${k}`)}</span>
                {kind === k && <Check className="h-4 w-4 text-green-400" />}
              </button>
            ))}
          </div>

          {/* Endpunkt (nur bei Remote-Engines) */}
          {needsUrl && (
            <div className="mb-5">
              <label className="mb-1.5 block text-xs text-white/40" htmlFor="setup-endpoint">
                {t('setup.endpointLabel')}
              </label>
              <input
                id="setup-endpoint"
                data-testid="setup-endpoint"
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder={
                  kind === 'openai_compatible' ? 'http://spark-xxx:8000/v1' : 'http://192.168.1.50:11434'
                }
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-white outline-none placeholder:text-white/20 focus:border-green-500/50"
              />
            </div>
          )}

          {/* Probe */}
          <button
            type="button"
            data-testid="setup-probe"
            onClick={() => void runProbe()}
            disabled={probing || (needsUrl && !endpoint.trim())}
            className="mb-5 flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/80 transition-colors hover:bg-white/[0.08] disabled:opacity-40"
          >
            {probing ? (
              <Loader2 className="h-4 w-4 animate-spin text-green-400" />
            ) : (
              <PlugZap className="h-4 w-4 text-green-400" />
            )}
            {t('setup.probe')}
          </button>

          {/* Status */}
          {probeState && (
            <div
              data-testid="setup-status"
              className={`mb-5 flex items-start gap-2 rounded-xl px-4 py-3 text-sm ${
                reachable
                  ? 'bg-green-500/10 text-green-300'
                  : 'bg-red-500/10 text-red-300'
              }`}
            >
              {reachable ? (
                <Check className="mt-0.5 h-4 w-4 flex-shrink-0" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              )}
              <span>{probeState.detail}</span>
            </div>
          )}

          {/* Modell-Auswahl */}
          {reachable && probeState && probeState.models.length > 0 && (
            <div className="mb-5">
              <label className="mb-1.5 block text-xs text-white/40" htmlFor="setup-model">
                {t('setup.modelLabel')}
              </label>
              <select
                id="setup-model"
                data-testid="setup-model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none focus:border-green-500/50"
              >
                {probeState.models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Fehler */}
          {error && (
            <div data-testid="setup-error" className="mb-5 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Übernehmen */}
          <button
            type="button"
            data-testid="setup-finish"
            onClick={() => void handleFinish()}
            disabled={!reachable || !model || saving}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-500 px-4 py-3.5 text-sm font-medium text-black transition-colors hover:bg-green-400 disabled:opacity-40"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('setup.finish')}
          </button>

          <button
            type="button"
            onClick={() => void handleReset()}
            className="mt-4 w-full text-center text-xs text-white/25 transition-colors hover:text-white/50"
          >
            {t('setup.reset')}
          </button>
        </div>
      </div>
    </ErrorBoundary>
  )
}
