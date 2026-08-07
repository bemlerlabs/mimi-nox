import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface WelcomeEmptyStateProps {
  onSuggestion: (text: string) => void
}

/** Chat-Leerzustand: Willkommens-Header + Vorschlags-Buttons (aus ChatLayout extrahiert) */
export default function WelcomeEmptyState({ onSuggestion }: WelcomeEmptyStateProps) {
  const { t } = useTranslation()
  const suggestions = [
    { title: t('chat.suggestions.0.title'), desc: t('chat.suggestions.0.desc') },
    { title: t('chat.suggestions.1.title'), desc: t('chat.suggestions.1.desc') },
    { title: t('chat.suggestions.2.title'), desc: t('chat.suggestions.2.desc') },
    { title: t('chat.suggestions.3.title'), desc: t('chat.suggestions.3.desc') },
  ]
  return (
    <motion.div
      initial={{ filter: 'blur(10px)', opacity: 0, y: 20 }}
      animate={{ filter: 'blur(0px)', opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center"
    >
      <div className="w-16 h-16 rounded-2xl liquid-glass-strong flex items-center justify-center mb-6 forest-glow">
        <Sparkles className="h-8 w-8 text-green-400" />
      </div>
      <h2 className="text-2xl font-bold text-white/90 mb-2">{t('chat.emptyStateTitle')}</h2>
      <p className="text-white/40 mb-8 max-w-md">
        {t('chat.emptyStateDesc')}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {suggestions.map((s: {title: string; desc: string}, i: number) => (
          <button
            key={i}
            className="liquid-glass-strong rounded-xl p-4 text-left hover:bg-green-500/5 transition-colors group"
            onClick={() => onSuggestion(s.title)}
          >
            <p className="text-sm text-white/70 group-hover:text-white/90 transition-colors">{s.title}</p>
            <p className="text-xs text-white/30 mt-1">{s.desc}</p>
          </button>
        ))}
      </div>
    </motion.div>
  )
}
