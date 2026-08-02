'use client'

import { motion } from 'framer-motion'
import { Card } from '@/components/ui'
import { useInView } from '@/hooks/useInView'
import { FileText, Code, FolderOpen, FileSpreadsheet, Scan, Image, BarChart3, Terminal, Search } from 'lucide-react'

const fadeUp = {
  hidden: { filter: 'blur(10px)', opacity: 0, y: 20 },
  visible: { filter: 'blur(0px)', opacity: 1, y: 0 },
}

interface SkillDef {
  icon: React.ComponentType<{ className?: string }>
  name: string
  desc: string
  depth: number // 0=canopy, 1=understory, 2=undergrowth
}

const skills: SkillDef[] = [
  { icon: FileText, name: '/write', desc: 'E-Mails, Notizen, Zusammenfassungen', depth: 2 },
  { icon: Code, name: '/review', desc: 'Code, Pläne, Dokumente reviewen', depth: 2 },
  { icon: FolderOpen, name: '/files', desc: 'Lokale Dateien lesen & analysieren', depth: 1 },
  { icon: FileSpreadsheet, name: '/pdf', desc: 'PDFs lesen, erstellen, analysieren', depth: 2 },
  { icon: Scan, name: '/scan', desc: 'Screenshots & Bilder analysieren', depth: 2 },
  { icon: Image, name: '/svg', desc: 'SVG-Assets entwerfen & erstellen', depth: 2 },
  { icon: BarChart3, name: '/chart', desc: 'Charts & Diagramme generieren', depth: 2 },
  { icon: Terminal, name: '/shell', desc: 'Shell-Befehle (approval-gated)', depth: 1 },
  { icon: Search, name: '/research', desc: 'Online-Recherche (opt-in)', depth: 0 },
]

const depthLabels: Record<number, string> = {
  0: 'Kronenschicht',
  1: 'Unterstand',
  2: 'Unterwuchs',
}

const depthColors: Record<number, string> = {
  0: 'text-green-300/50',
  1: 'text-green-400/50',
  2: 'text-lichen/40',
}

export default function SkillsSection() {
  const { ref, isInView } = useInView(0.05)

  return (
    <section ref={ref} className="relative py-32 px-6 md:px-12 lg:px-20 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-black via-moss-deep/[0.04] to-black pointer-events-none" />
      
      {/* Canopy light rays */}
      <div className="absolute top-0 left-1/4 right-1/4 h-[400px] pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-b from-green-400/[0.02] to-transparent rotate-[-5deg] origin-top" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="inline-block text-xs font-medium text-green-400/50 uppercase tracking-[0.25em] mb-4">Skills</span>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mt-2 mb-6">
            <span className="text-gradient">Unterwuchs.</span>{' '}
            <span className="text-white/60">Viele Wege nach oben.</span>
          </h2>
          <p className="text-white/40 max-w-xl mx-auto text-base leading-relaxed">
            Wie im Schwarzwald wächst ein ganzer Ökosystem an Fähigkeiten —
            von tiefen Tools bis zu leichten Befehlen. Einfach <code className="text-green-400/60 font-mono text-sm">/</code> tippen.
          </p>
        </motion.div>

        {/* Legend */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex flex-wrap justify-center gap-4 mb-12"
        >
          {Object.entries(depthLabels).map(([level, label]) => (
            <div key={level} className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${level === '0' ? 'bg-green-300/50' : level === '1' ? 'bg-green-400/50' : 'bg-lichen/40'}`} />
              <span className={`text-xs ${depthColors[Number(level)]} uppercase tracking-wider`}>
                {label}
              </span>
            </div>
          ))}
        </motion.div>

        {/* Skills Grid — arranged by depth */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.map((s, i) => (
            <motion.div
              key={s.name}
              initial="hidden"
              animate={isInView ? 'visible' : 'hidden'}
              variants={fadeUp}
              transition={{ duration: 0.4, delay: 0.06 * i }}
            >
              <Card className="group relative flex items-start gap-3.5 p-4 bg-gradient-to-r from-moss/[0.04] to-moss/[0.01] border border-moss/8 group-hover:border-moss/20 transition-all duration-300 noise-overlay">
                {/* Depth indicator */}
                <div className={`absolute top-2 ${s.depth === 0 ? 'left-2' : s.depth === 1 ? 'left-3' : 'left-3.5'} w-1 h-6 rounded-full ${s.depth === 0 ? 'bg-green-300/20' : s.depth === 1 ? 'bg-green-400/20' : 'bg-lichen/15'}`} />
                
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-1.5">
                    <s.icon className="h-4 w-4 text-green-400/70 group-hover:text-green-400 transition-colors" />
                    <code className="text-sm font-mono text-green-300/80 group-hover:text-green-300 transition-colors">{s.name}</code>
                  </div>
                  <p className="text-xs text-white/30 group-hover:text-white/40 transition-colors">{s.desc}</p>
                </div>

                {/* Hover glow */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-green-400/[0.01] pointer-events-none" />
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Bottom note */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="text-center mt-12"
        >
          <p className="text-xs text-white/20">
            + 12+ weitere Skills verfügbar — <span className="text-green-400/40 cursor-pointer hover:text-green-400/60 transition-colors">alle erweitern</span>
          </p>
        </motion.div>
      </div>
    </section>
  )
}