import { useTranslation } from 'react-i18next'

/**
 * Hook to toggle app language between de and en.
 * Saves preference to localStorage via i18next.
 */
export function useToggleLanguage() {
  const { i18n } = useTranslation()

  const toggle = () => {
    const next = i18n.language === 'de' ? 'en' : 'de'
    i18n.changeLanguage(next)
  }

  return { toggle, currentLang: i18n.language }
}