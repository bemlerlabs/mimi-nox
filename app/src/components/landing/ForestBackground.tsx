import { useEffect, useRef } from 'react'

/**
 * Black Forest Background — schwebende Partikel wie Feuerfliegen im dunklen Wald
 * Läuft über die gesamte Seite, performant mit Canvas
 */
export default function ForestBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    let particles: Array<{
      x: number
      y: number
      size: number
      speedX: number
      speedY: number
      opacity: number
      pulseSpeed: number
      pulseOffset: number
    }> = []

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = document.documentElement.scrollHeight
    }

    const init = () => {
      resize()
      particles = []
      const count = Math.floor((canvas.width * canvas.height) / 15000)
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 2.5 + 0.5,
          speedX: (Math.random() - 0.5) * 0.3,
          speedY: (Math.random() - 0.5) * 0.2 - 0.1,
          opacity: Math.random() * 0.5 + 0.1,
          pulseSpeed: Math.random() * 0.02 + 0.005,
          pulseOffset: Math.random() * Math.PI * 2,
        })
      }
    }

    const draw = (time: number) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Dark forest gradient overlay
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height)
      gradient.addColorStop(0, 'rgba(0, 0, 0, 0.3)')
      gradient.addColorStop(0.3, 'rgba(0, 20, 5, 0.15)')
      gradient.addColorStop(0.6, 'rgba(0, 15, 3, 0.1)')
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0.3)')
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Draw particles (fireflies)
      for (const p of particles) {
        const pulse = Math.sin(time * p.pulseSpeed + p.pulseOffset) * 0.3 + 0.7
        const alpha = p.opacity * pulse

        // Glow effect
        const glowSize = p.size * 3
        const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowSize)
        glow.addColorStop(0, `rgba(34, 197, 94, ${alpha * 0.6})`)
        glow.addColorStop(0.5, `rgba(34, 197, 94, ${alpha * 0.2})`)
        glow.addColorStop(1, 'rgba(34, 197, 94, 0)')
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(p.x, p.y, glowSize, 0, Math.PI * 2)
        ctx.fill()

        // Core particle
        ctx.fillStyle = `rgba(134, 239, 172, ${alpha})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()

        // Move
        p.x += p.speedX
        p.y += p.speedY

        // Wrap around
        if (p.x < 0) p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
      }

      animationId = requestAnimationFrame(draw)
    }

    init()
    animationId = requestAnimationFrame(draw)

    let resizeTimeout: ReturnType<typeof setTimeout>
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout)
      resizeTimeout = setTimeout(init, 200)
    })

    let scrollTimeout: ReturnType<typeof setTimeout>
    window.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout)
      scrollTimeout = setTimeout(() => {
        canvas.height = document.documentElement.scrollHeight
      }, 100)
    }, { passive: true })

    return () => {
      cancelAnimationFrame(animationId)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.8 }}
    />
  )
}
