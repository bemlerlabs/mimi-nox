import { AlertCircle, ArrowRight, CheckCircle, Loader2 } from 'lucide-react'

export interface OllamaStatus {
  healthy: boolean
  version?: string
  endpoint: string
}

interface OllamaCheckProps {
  status: OllamaStatus | null
  loading: boolean
  error: string
  onCheck: () => void
}

/** Step 1 — prüft, ob Ollama installiert und läuft (check_ollama) */
export default function OllamaCheck({ status, loading, error, onCheck }: OllamaCheckProps) {
  return (
    <div className="text-center space-y-6">
      <div className="text-6xl">🦙</div>
      <h2 className="text-2xl font-bold">Ollama entdecken</h2>
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
      {status && (
        <div className="bg-white/5 rounded-lg p-4 space-y-2 text-left">
          <div className="flex items-center gap-2">
            {status.healthy ? (
              <CheckCircle className="w-5 h-5 text-green-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-400" />
            )}
            <span className={status.healthy ? 'text-green-400' : 'text-amber-400'}>
              {status.healthy ? 'Ollama läuft!' : 'Ollama nicht gefunden'}
            </span>
          </div>
          {status.version && <p className="text-xs text-white/50">Version: {status.version}</p>}
          <p className="text-xs text-white/30">Endpoint: {status.endpoint}</p>
        </div>
      )}
      <button
        onClick={onCheck}
        disabled={loading}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg py-3 px-4 font-medium flex items-center justify-center gap-2 transition-all"
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
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
  )
}
