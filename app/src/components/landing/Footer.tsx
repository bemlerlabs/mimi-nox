import { Github } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-moss/8 relative z-10">
      <div className="max-w-6xl mx-auto px-6 md:px-12 lg:px-20 py-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-400/40" />
            {/* WCAG AA (Sprint2-F2): Opacitaeten so, dass gerendert >= 4.5:1
                auf black-forest (hsl(0 0% 2%)) — green-400 voll = 11.7:1,
                white/55 = 6.3:1. Regression: Lighthouse color-contrast. */}
            <span className="text-sm text-green-400 font-medium">MiMi Nox</span>
            <span className="text-[10px] text-white/45">·</span>
            <span className="text-xs text-white/55">Privat. Lokal. Dein.</span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/bemlerlabs/mimi-nox"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-white/55 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <a
              href="https://miminox.app/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/55 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              Dokumentation
            </a>
            <a
              href="https://miminox.app/changelog"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/55 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              Changelog
            </a>
          </div>

          {/* Legal */}
          <div className="flex items-center gap-3 text-xs text-white/55">
            <span>© {currentYear} MiMiTechAi</span>
            <span>·</span>
            <span>Apache 2.0</span>
          </div>
        </div>
      </div>
    </footer>
  )
}