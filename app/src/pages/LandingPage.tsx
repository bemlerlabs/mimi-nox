import { useTranslation } from 'react-i18next'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import LivingForest from '@/components/landing/LivingForest'
import HeroSection from '@/components/landing/HeroSection'
import FeaturesSection from '@/components/landing/FeaturesSection'
import ArchitectureSection from '@/components/landing/ArchitectureSection'
import SkillsSection from '@/components/landing/SkillsSection'
import CTASection from '@/components/landing/CTASection'
import Footer from '@/components/landing/Footer'

export default function LandingPage() {
  const { t } = useTranslation()

  return (
    <ErrorBoundary fallback={
      <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-black-forest">
        <p className="text-white/50 mb-4">{t('error.fallback')}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-colors"
          aria-label={t('settings.reload')}
        >
          {t('settings.reload')}
        </button>
      </div>
    }>
      <div className="relative min-h-screen bg-black-forest overflow-hidden">
        <LivingForest />
        <main id="main-content" className="relative z-10">
          <HeroSection />
          <FeaturesSection />
          <ArchitectureSection />
          <SkillsSection />
          <CTASection />
          <Footer />
        </main>
      </div>
    </ErrorBoundary>
  )
}