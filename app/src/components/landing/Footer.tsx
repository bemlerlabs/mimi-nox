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
            <span className="text-sm text-green-400/50 font-medium">MiMi Nox</span>
            <span className="text-[10px] text-white/15">·</span>
            <span className="text-xs text-white/20">Privat. Lokal. Dein.</span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/MimiTechAi/mimi-nox"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-white/25 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <a
              href="https://miminox.app/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/25 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              Dokumentation
            </a>
            <a
              href="https://miminox.app/changelog"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/25 hover:text-green-400 transition-colors duration-200 text-xs"
            >
              Changelog
            </a>
          </div>

          {/* Legal */}
          <div className="flex items-center gap-3 text-xs text-white/15">
            <span>© {currentYear} MiMiTechAi</span>
            <span>·</span>
            <span>Apache 2.0</span>
          </div>
        </div>
      </div>
    </footer>
  )
}