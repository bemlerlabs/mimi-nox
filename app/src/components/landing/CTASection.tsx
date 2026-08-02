'use client'

import { motion } from 'framer-motion'
import { useInView } from '@/hooks/useInView'
import { Apple, Monitor, Globe, ArrowRight, Download, ExternalLink } from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'

const fadeUp = {
  hidden: { filter: 'blur(10px)', opacity: 0, y: 20 },
  visible: { filter: 'blur(0px)', opacity: 1, y: 0 },
}

interface PlatformDef {
  id: 'macos-arm64' | 'macos-x86' | 'windows' | 'linux' | 'web'
  label: string
  icon: React.ComponentType<{ className?: string }>
  desc: string
  url: string
  badge?: string
}

export default function CTASection() {
  const { ref, isInView } = useInView(0.1)
  const [detectedPlatform, setDetectedPlatform] = useState<string>('')
  const [hoveredPlatform, setHoveredPlatform] = useState<string | null>(null)

  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase()
    if (ua.includes('mac') || ua.includes('iphone') || ua.includes('ipad')) {
      setDetectedPlatform(ua.includes('arm') || ua.includes('silicon') ? 'macos-arm64' : 'macos-x86')
    } else if (ua.includes('windows')) {
      setDetectedPlatform('windows')
    } else if (ua.includes('linux')) {
      setDetectedPlatform('linux')
    } else {
      setDetectedPlatform('web')
    }
  }, [])

  const platforms: PlatformDef[] = [
    {
      id: 'macos-arm64',
      label: 'macOS',
      icon: Apple,
      desc: 'Apple Silicon (M1/M2/M3/M4) — native',
      url: 'https://releases.miminox.app/darwin/arm64/miminox.dmg',
      badge: 'Empfohlen',
    },
    {
      id: 'macos-x86',
      label: 'macOS',
      icon: Apple,
      desc: 'Intel (x86_64) — universal binary',
      url: 'https://releases.miminox.app/darwin/x64/miminox.dmg',
    },
    {
      id: 'windows',
      label: 'Windows',
      icon: Monitor,
      desc: 'Windows 10/11 — 64-bit',
      url: 'https://releases.miminox.app/windows/x64/miminox-setup.exe',
    },
    {
      id: 'linux',
      label: 'Linux',
      icon: Monitor,
      desc: 'AppImage · .deb · .rpm',
      url: 'https://releases.miminox.app/linux/appimage/miminox.AppImage',
      badge: 'Multi-Format',
    },
    {
      id: 'web',
      label: 'Web / PWA',
      icon: Globe,
      desc: 'Im Browser — kein Install nötig',
      url: '/chat',
    },
  ]

  const handleDownload = useCallback((platformId: string) => {
    if (platformId === 'web') return // handled by routing
    // In production, track download events
    console.log('Download:', platformId)
  }, [])

  return (
    <section ref={ref} className="relative py-32 px-6 md:px-12 lg:px-20 overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-[0.04]"
          style={{
            background: 'radial-gradient(circle, hsl(142 65% 55%) 0%, transparent 70%)',
            filter: 'blur(120px)',
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black via-moss-deep/[0.03] to-black" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="inline-block text-xs font-medium text-green-400/50 uppercase tracking-[0.25em] mb-4">Download</span>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mt-2 mb-6">
            <span className="text-gradient">Starte jetzt.</span>
          </h2>
          <p className="text-white/40 max-w-lg mx-auto text-base leading-relaxed">
            {detectedPlatform ? (
              <>
                <span className="text-green-400/70">
                  {detectedPlatform === 'web' ? 'Web' : detectedPlatform === 'windows' ? 'Windows' : detectedPlatform.startsWith('macos') ? 'macOS' : 'Linux'} erkannt
                </span>
                {' '}— Du kannst jederzeit eine andere Plattform wählen.
              </>
            ) : (
              'Kein Account. Kein Cloud. Kein Tracking. Einfach installieren und loslegen.'
            )}
          </p>
        </motion.div>

        {/* Platform Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {platforms.map((p, i) => {
            const isDefault = p.id === detectedPlatform
            const Icon = p.icon

            return (
              <motion.div
                key={p.id}
                initial="hidden"
                animate={isInView ? 'visible' : 'hidden'}
                variants={fadeUp}
                transition={{ duration: 0.5, delay: 0.08 * i }}
                onMouseEnter={() => setHoveredPlatform(p.id)}
                onMouseLeave={() => setHoveredPlatform(null)}
              >
                <div className="relative group">
                  {/* Default platform glow */}
                  {isDefault && (
                    <div className="absolute -inset-0.5 rounded-2xl bg-green-400/10 blur-md opacity-60 group-hover:opacity-80 transition-opacity" />
                  )}

                  <div className={`relative liquid-glass rounded-2xl p-6 h-full transition-all duration-500 ${
                    isDefault
                      ? 'border-green-400/20 bg-moss/[0.06]'
                      : 'border-moss/10 bg-gradient-to-b from-moss/[0.04] to-moss/[0.01]'
                  } group-hover:border-moss-light/20 noise-overlay`}>
                    {/* Header row */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500 ${
                          isDefault ? 'bg-green-500/15 forest-glow-subtle' : 'bg-moss/10 group-hover:bg-green-500/10'
                        }`}>
                          <Icon className={`h-5 w-5 transition-colors ${
                            isDefault ? 'text-green-400' : 'text-white/30 group-hover:text-green-400/70'
                          }`} />
                        </div>
                        <div>
                          <h3 className="text-base font-semibold text-white/90">{p.label}</h3>
                          {isDefault && (
                            <span className="text-[10px] text-green-400 font-medium uppercase tracking-wider">
                              Empfohlen
                            </span>
                          )}
                        </div>
                      </div>
                      {p.badge && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-400/10 text-green-400/70 border border-green-400/10">
                          {p.badge}
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-xs text-white/30 mb-5 leading-relaxed">{p.desc}</p>

                    {/* Download Button */}
                    {p.id === 'web' ? (
                      <a
                        href={p.url}
                        className="inline-flex items-center justify-center gap-2 w-full bg-green-500/10 hover:bg-green-500/15 border border-green-400/10 hover:border-green-400/20 text-green-400 rounded-xl h-10 text-sm font-medium transition-all duration-300"
                      >
                        <Globe className="h-4 w-4" />
                        MiMi Nox starten
                        <ArrowRight className="h-3.5 w-3.5" />
                      </a>
                    ) : (
                      <a
                        href={p.url}
                        onClick={() => handleDownload(p.id)}
                        className="inline-flex items-center justify-center gap-2 w-full bg-green-500/10 hover:bg-green-500/15 border border-green-400/10 hover:border-green-400/20 text-green-400 rounded-xl h-10 text-sm font-medium transition-all duration-300"
                      >
                        <Download className="h-4 w-4" />
                        Download
                        {hoveredPlatform === p.id && <ExternalLink className="h-3.5 w-3.5 opacity-50" />}
                      </a>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Alternative install methods */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center"
        >
          <div className="liquid-glass-strong rounded-2xl p-5 max-w-xl mx-auto">
            <p className="text-[10px] text-white/25 uppercase tracking-[0.2em] mb-3">Alternativ</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 text-xs">
              <code className="text-green-400/60 font-mono bg-black/30 px-3 py-1.5 rounded-lg">
                npm create miminox@latest
              </code>
              <span className="text-white/15">oder</span>
              <code className="text-green-400/60 font-mono bg-black/30 px-3 py-1.5 rounded-lg">
                pip install miminox
              </code>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}