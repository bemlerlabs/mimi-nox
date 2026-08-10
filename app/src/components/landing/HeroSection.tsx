'use client'

import { motion } from 'framer-motion'
import { Github, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui'
import { useInView } from '@/hooks/useInView'
import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

const fadeUp = {
  hidden: { filter: 'blur(10px)', opacity: 0, y: 20 },
  visible: { filter: 'blur(0px)', opacity: 1, y: 0 },
}

const STAGGER = 0.12

// Platform auto-detect
function usePlatform() {
  const [platform, setPlatform] = useState<'macos' | 'windows' | 'linux' | 'web' | 'unknown'>('unknown')

  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase()
    if (ua.includes('mac') || ua.includes('iphone') || ua.includes('ipad')) setPlatform('macos')
    else if (ua.includes('windows')) setPlatform('windows')
    else if (ua.includes('linux')) setPlatform('linux')
    else setPlatform('web')
  }, [])

  return platform
}

export default function HeroSection() {
  const { t } = useTranslation()
  const { ref, isInView } = useInView(0.1)
  const platform = usePlatform()
  const [installCopied, setInstallCopied] = useState(false)

  const installCmd = platform === 'windows'
    ? 'winget install MiMiNox'
    : platform === 'linux'
    ? 'curl -fsSL https://releases.miminox.app/install.sh | bash'
    : 'brew install mimitech/tap/miminox'

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(installCmd).then(() => {
      setInstallCopied(true)
      setTimeout(() => setInstallCopied(false), 2500)
    })
  }, [installCmd])

  return (
    <section ref={ref} className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Ambient glow behind title */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          className="w-[800px] h-[800px] rounded-full opacity-[0.07]"
          style={{
            background: 'radial-gradient(circle, hsl(142 65% 55%) 0%, transparent 70%)',
            filter: 'blur(100px)',
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center px-6 max-w-5xl mx-auto pt-24 pb-20">
        {/* Badge */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="flex justify-center mb-10"
        >
          <span className="inline-flex items-center gap-2 liquid-glass rounded-full px-5 py-2 text-xs font-medium text-green-400/80 tracking-wide">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-50" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
            </span>
            {t('hero.badge')}
          </span>
        </motion.div>

        {/* Brand: MiMi (Instrument Serif italics) + Nox (white) */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8 }}
          className="mb-4"
        >
          <h1 className="text-6xl sm:text-7xl md:text-8xl lg:text-[9rem] font-normal leading-[0.9] tracking-tight select-none">
            <em className="text-gradient font-display" style={{ fontFamily: '"Instrument Serif", serif' }}>{t('hero.title')}</em>
            <span className="text-stone font-display"> Nox</span>
          </h1>
        </motion.div>

        {/* Tagline */}
        <motion.h2
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8, delay: STAGGER * 1 }}
          className="text-2xl sm:text-3xl md:text-4xl font-medium text-white/70 mb-6 mt-4"
        >
          {t('hero.headline')}
        </motion.h2>

        {/* Subtitle */}
        <motion.p
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8, delay: STAGGER * 2 }}
          className="text-base sm:text-lg text-white/40 mb-12 max-w-2xl mx-auto leading-relaxed"
        >
          {t('hero.subtitle')}
          <br />
          {t('app.description')}
        </motion.p>

        {/* Install Command */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8, delay: STAGGER * 3 }}
          className="liquid-glass-strong rounded-2xl p-5 max-w-xl mx-auto mb-12"
        >
          <p className="text-[10px] text-white/30 uppercase tracking-[0.2em] mb-3">{t('hero.installSubtext')}</p>
          <div className="flex items-center gap-3 bg-black/60 rounded-xl p-4 border border-white/5">
            <code className="flex-1 text-sm font-mono text-green-400/90 break-all text-left leading-relaxed">
              {installCmd}
            </code>
            <button
              onClick={handleCopy}
              className="liquid-glass rounded-lg px-3 py-2 text-xs hover:bg-green-500/10 transition-all flex items-center gap-1.5 flex-shrink-0 group"
              aria-label={t('hero.copy')}
            >
              {installCopied ? (
                <>
                  <svg className="h-3.5 w-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-green-400">{t('hero.copySuccess')}</span>
                </>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5 text-white/40 group-hover:text-white/70 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  <span className="text-white/40 group-hover:text-white/70 transition-colors">{t('hero.copy')}</span>
                </>
              )}
            </button>
          </div>
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8, delay: STAGGER * 4 }}
          className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
        >
          <Button variant="primary" size="lg" className="text-base">
            {t('hero.startNow')}
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
          <a
            href="https://github.com/bemlerlabs/mimi-nox"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-xl font-medium h-12 px-6 text-base gap-2.5 liquid-glass hover:bg-green-500/10 text-white/80 hover:text-white transition-all duration-300"
          >
            <Github className="h-4 w-4" />
            {t('nav.github')}
          </a>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.8, delay: STAGGER * 5 }}
          className="flex flex-wrap justify-center gap-3"
        >
          {[
            { value: '7,000+', label: t('a11y.activeUsers') },
            { value: '100%', label: t('a11y.offline') },
            { value: 'Apache 2.0', label: t('a11y.openSource') },
          ].map((stat, i) => (
            <div key={i} className="liquid-glass rounded-xl px-5 py-3 text-center min-w-[120px]">
              <div className="text-base font-semibold text-green-400">{stat.value}</div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider mt-0.5">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : { opacity: 0 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-[10px] text-white/20 uppercase tracking-widest">{t('hero.scrollHint')}</span>
        <div className="w-px h-8 bg-gradient-to-b from-white/20 to-transparent" />
      </motion.div>
    </section>
  )
}