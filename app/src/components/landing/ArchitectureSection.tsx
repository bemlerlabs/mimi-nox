'use client'

import { motion } from 'framer-motion'
import { Card } from '@/components/ui'
import { useInView } from '@/hooks/useInView'

const fadeUp = {
  hidden: { filter: 'blur(10px)', opacity: 0, y: 20 },
  visible: { filter: 'blur(0px)', opacity: 1, y: 0 },
}

interface NodeDef {
  label: string
  desc: string
  port: string
  color: string
}

const nodes: NodeDef[] = [
  { label: 'Browser PWA', desc: 'Dein Interface auf Desktop oder Handy', port: ':5173', color: 'green' },
  { label: 'FastAPI Server', desc: 'Lokaler Python-Server, orchestriert alles', port: ':8765', color: 'amber' },
  { label: 'Ollama', desc: 'Lokales LLM — gemma4:e4b', port: ':11434', color: 'green' },
]

export default function ArchitectureSection() {
  const { ref, isInView } = useInView(0.1)

  return (
    <section ref={ref} className="relative py-32 px-6 md:px-12 lg:px-20 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-black via-moss-deep/[0.03] to-black pointer-events-none" />
      
      {/* Root system decorative lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-[0.03]" aria-hidden="true">
        {/* Main trunk */}
        <path d="M50% 0 C50% 15%, 45% 30%, 48% 50%, 52% 70%, 50% 85%, 47% 100%" stroke="hsl(142 40% 25%)" strokeWidth="2" fill="none" />
        {/* Left branches */}
        <path d="M48% 20 C35% 22%, 20% 35%, 10% 55%" stroke="hsl(142 40% 25%)" strokeWidth="1.5" fill="none" />
        <path d="M50% 35 C65% 38%, 80% 50%, 90% 70%" stroke="hsl(142 40% 25%)" strokeWidth="1.5" fill="none" />
        <path d="M48% 50 C30% 52%, 15% 65%, 5% 90%" stroke="hsl(142 40% 25%)" strokeWidth="1" fill="none" />
        <path d="M52% 65 C70% 68%, 85% 80%, 95% 95%" stroke="hsl(142 40% 25%)" strokeWidth="1" fill="none" />
        {/* Fine roots */}
        <path d="M35% 25 C25% 28%, 15% 40%" stroke="hsl(142 35% 20%)" strokeWidth="0.5" fill="none" />
        <path d="M65% 40 C75% 43%, 85% 55%" stroke="hsl(142 35% 20%)" strokeWidth="0.5" fill="none" />
        <path d="M30% 55 C20% 58%, 10% 70%" stroke="hsl(142 35% 20%)" strokeWidth="0.5" fill="none" />
      </svg>

      <div className="relative z-10 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="inline-block text-xs font-medium text-green-400/50 uppercase tracking-[0.25em] mb-4">Architektur</span>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mt-2 mb-6">
            <span className="text-gradient">Ein Wurzel-System.</span>
          </h2>
          <p className="text-white/40 max-w-xl mx-auto text-base leading-relaxed">
            Wie im Schwarzwald verbinden sich Schichten tief mit dem Boden. 
            Keine Pfeile — sondern organische Verbindungen, die alles zusammenhalten.
          </p>
        </motion.div>

        {/* Node cards with root connections */}
        <div className="relative">
          {/* Connection line (trunk) */}
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-green-400/10 via-moss/20 to-transparent -translate-x-1/2 hidden md:block pointer-events-none" />

          <div className="flex flex-col gap-8 md:gap-0">
            {nodes.map((node, i) => (
              <motion.div
                key={node.label}
                initial="hidden"
                animate={isInView ? 'visible' : 'hidden'}
                variants={fadeUp}
                transition={{ duration: 0.6, delay: 0.15 * i }}
                className={`relative ${i % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'} flex items-stretch gap-0`}
              >
                {/* Node card */}
                <div className={`flex-1 ${i % 2 === 0 ? 'md:justify-end md:pr-12' : 'md:justify-start md:pl-12'}`}>
                  <Card className={`relative max-w-sm group transition-all duration-500 ${i % 2 === 0 ? 'md:text-right' : 'md:text-left'} bg-gradient-to-b from-moss/[0.06] to-moss/[0.02] border border-moss/10 group-hover:border-moss-light/20 noise-overlay`}>
                    {/* Color accent dot */}
                    <div className={`absolute top-3 ${i % 2 === 0 ? 'right-3' : 'left-3'} w-2 h-2 rounded-full ${node.color === 'green' ? 'bg-green-400' : 'bg-amber-400'} opacity-60 group-hover:opacity-100 transition-opacity`} />
                    
                    <div className={`pr-8 ${i % 2 === 0 ? 'pr-8' : 'pl-8 pt-0'}`}>
                      {/* Icon row */}
                      <div className={`flex items-center gap-2 mb-2 ${i % 2 === 0 ? 'md:justify-end' : 'md:justify-start'}`}>
                        <span className="text-[10px] font-mono text-white/20">{node.port}</span>
                      </div>
                      
                      <h3 className="text-lg font-semibold text-white/90 mb-1">{node.label}</h3>
                      <p className="text-sm text-white/40 leading-relaxed">{node.desc}</p>
                    </div>
                  </Card>
                </div>

                {/* Center node dot */}
                <div className="hidden md:flex items-center justify-center w-8 flex-shrink-0">
                  <div className="w-3 h-3 rounded-full bg-green-400/30 border border-green-400/40 relative">
                    <div className="absolute inset-0 rounded-full bg-green-400/20 animate-ping" />
                  </div>
                </div>

                {/* Spacer for opposite side */}
                <div className="hidden md:block flex-1" />
              </motion.div>
            ))}
          </div>

          {/* Bottom: "Roots" — additional context */}
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={fadeUp}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="mt-16 md:mt-24"
          >
            <div className="relative max-w-2xl mx-auto">
              {/* Decorative roots at bottom */}
              <svg className="absolute bottom-full left-0 right-0 h-24 pointer-events-none opacity-[0.04]" viewBox="0 0 800 100" preserveAspectRatio="none">
                <path d="M400 0 C380 20, 350 40, 320 60, 290 80, 250 90, 200 100" stroke="white" strokeWidth="2" fill="none" />
                <path d="M400 0 C420 20, 450 40, 480 60, 510 80, 550 90, 600 100" stroke="white" strokeWidth="2" fill="none" />
                <path d="M400 0 C390 25, 370 50, 340 75, 310 90, 280 100" stroke="white" strokeWidth="1.5" fill="none" />
                <path d="M400 0 C410 25, 430 50, 460 75, 490 90, 520 100" stroke="white" strokeWidth="1.5" fill="none" />
              </svg>

              <div className="liquid-glass-strong rounded-2xl p-6 border border-moss/10">
                <pre className="text-xs font-mono text-green-400/60 leading-relaxed">
{`Browser PWA    →    FastAPI Server    →    Ollama (local)
   :5173           :8765               :11434
   React           Python              gemma4:e4b
   WebSocket       REST API            Local GPU/CPU`}
                </pre>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}