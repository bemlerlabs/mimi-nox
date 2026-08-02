import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'

export default function TypingIndicator() {
  const { isTyping } = useChatStore()

  if (!isTyping) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="flex items-center gap-3 p-4"
    >
      <div className="w-8 h-8 rounded-full liquid-glass flex items-center justify-center forest-glow-subtle">
        <Sparkles className="h-4 w-4 text-green-400" />
      </div>
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-green-400"
            animate={{ scale: [0.8, 1.2, 0.8] }}
            transition={{
              duration: 1,
              repeat: Infinity,
              delay: i * 0.2,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      <span className="text-sm text-white/50">MiMi Nox denkt nach...</span>
    </motion.div>
  )
}
