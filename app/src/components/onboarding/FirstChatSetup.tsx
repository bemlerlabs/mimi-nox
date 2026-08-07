import { ArrowRight, CheckCircle } from 'lucide-react'

interface FirstChatSetupProps {
  onComplete: () => void
}

/** Step 3 — Willkommen + Start in den Chat */
export default function FirstChatSetup({ onComplete }: FirstChatSetupProps) {
  return (
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
        onClick={onComplete}
        className="w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white rounded-lg py-3 px-4 font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-violet-500/20"
      >
        <ArrowRight className="w-5 h-5" />
        MiMi Nox starten
      </button>
    </div>
  )
}
