'use client'

import { motion } from 'framer-motion'
import { Card } from '@/components/ui'
import { useInView } from '@/hooks/useInView'
import { Shield, Eye, Brain, Zap } from 'lucide-react'

const fadeUp = {
  hidden: { filter: 'blur(10px)', opacity: 0, y: 20 },
  visible: { filter: 'blur(0px)', opacity: 1, y: 0 },
}

interface FeatureCard {
  icon: React.ComponentType<{ className?: string }>
  title: string
  desc: string
  tag: string
}

const features: FeatureCard[] = [
  {
    icon: Shield,
    title: 'Offline-first',
    desc: 'Offline-first via Ollama + gemma4:e4b. Kein Internet nötig. Deine Daten bleiben auf deinem Gerät.',
    tag: 'Privacy',
  },
  {
    icon: Eye,
    title: 'Multimodal',
    desc: 'Bilder, PDFs, Dateien, Screenshots — MiMi Nox versteht und analysiert alles was du ihm gibst.',
    tag: 'Vision',
  },
  {
    icon: Brain,
    title: 'Memory',
    desc: 'Semantischer Vektorspeicher mit ChromaDB. MiMi Nox erinnert sich an Kontext, Präferenzen und Fakten.',
    tag: 'Knowledge',
  },
  {
    icon: Zap,
    title: 'Tools',
    desc: 'Shell, Web Search, Browser, Dateisystem — alles approval-gated. Du behältst die Kontrolle.',
    tag: 'Power',
  },
]

export default function FeaturesSection() {
  const { ref, isInView } = useInView(0.1)

  return (
    <section ref={ref} className="relative py-32 px-6 md:px-12 lg:px-20 overflow-hidden">
      {/* Section background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-black via-moss-deep/[0.03] to-black pointer-events-none" />
      
      {/* Decorative root-like lines */}
      <div className="absolute top-1/2 left-0 right-0 h-px bg-gradient-to-r from-transparent via-moss/20 to-transparent pointer-events-none" />
      <div className="absolute top-[45%] left-1/4 w-px h-[200px] bg-gradient-to-b from-moss/10 to-transparent pointer-events-none" />
      <div className="absolute top-[45%] right-1/4 w-px h-[200px] bg-gradient-to-b from-moss/10 to-transparent pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="inline-block text-xs font-medium text-green-400/50 uppercase tracking-[0.25em] mb-4">Features</span>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mt-2 mb-6">
            <span className="text-gradient">Alles lokal.</span>{' '}
            <span className="text-white/60">Alles privat.</span>
          </h2>
          <p className="text-white/40 max-w-xl mx-auto text-base leading-relaxed">
            MiMi Nox läuft komplett auf deinem Gerät. Kein Cloud-Sync, kein Account, kein Tracking.
          </p>
        </motion.div>

        {/* Feature Cards — Moss-Covered-Stone Design */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial="hidden"
              animate={isInView ? 'visible' : 'hidden'}
              variants={fadeUp}
              transition={{ duration: 0.5, delay: 0.1 * i }}
            >
              <div className="relative group h-full">
                {/* Moss cover overlay */}
                <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-b from-green-500/[0.08] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm" />
                
                <Card className="h-full relative bg-gradient-to-b from-moss/[0.06] to-moss/[0.02] border border-moss/10 group-hover:border-moss-light/20 transition-all duration-500 noise-overlay">
                  {/* Moss corner */}
                  <div className="absolute top-0 right-0 w-16 h-16 overflow-hidden pointer-events-none">
                    <div className="absolute top-[-8px] right-[-8px] w-20 h-20 rounded-full bg-moss-deep/[0.15] blur-xl" />
                  </div>

                  {/* Icon */}
                  <div className="relative mb-6">
                    <div className="w-12 h-12 rounded-xl liquid-glass flex items-center justify-center group-hover:forest-glow-subtle transition-all duration-500">
                      <f.icon className="h-5 w-5 text-green-400" />
                    </div>
                  </div>

                  {/* Tag */}
                  <span className="relative text-[10px] font-medium text-green-400/40 uppercase tracking-wider">
                    {f.tag}
                  </span>

                  {/* Title */}
                  <h3 className="relative text-lg font-semibold text-white/90 mt-2 mb-3">
                    {f.title}
                  </h3>

                  {/* Description */}
                  <p className="relative text-sm text-white/40 leading-relaxed">
                    {f.desc}
                  </p>

                  {/* Bottom accent line */}
                  <div className="relative mt-6 h-px bg-gradient-to-r from-green-400/20 to-transparent w-0 group-hover:w-full transition-all duration-700" />
                </Card>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}