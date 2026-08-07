import { AlertCircle, Download, Loader2 } from 'lucide-react'

export interface PullProgress {
  model_id: string
  status: string
  percentage?: number
  total?: string
  completed?: string
}

interface ModelSelectorProps {
  progress: PullProgress | null
  loading: boolean
  error: string
  onPull: () => void
}

/** Step 2 — wählt das Modell aus und lädt es herunter (pull_model) */
export default function ModelSelector({ progress, loading, error, onPull }: ModelSelectorProps) {
  return (
    <div className="text-center space-y-6">
      <div className="text-6xl">🤖</div>
      <h2 className="text-2xl font-bold">Modell herunterladen</h2>
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
      {progress && (
        <div className="bg-white/5 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-white/70">{progress.model_id}</span>
            <span className="text-violet-400">{progress.percentage}%</span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-violet-500 to-purple-400 h-full rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage || 0}%` }}
            />
          </div>
          <p className="text-xs text-white/40">{progress.status}</p>
        </div>
      )}
      <button
        onClick={onPull}
        disabled={loading}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg py-3 px-4 font-medium flex items-center justify-center gap-2 transition-all"
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
        {progress ? 'Erneut herunterladen' : 'Miminox herunterladen'}
      </button>
    </div>
  )
}
