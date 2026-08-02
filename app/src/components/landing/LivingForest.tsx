import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * Living Forest — Schwarzwald-Atmosphäre auf Canvas
 * 
 * 3 Layer:
 * 1. Nebel-Blobs (radial gradients, parallax-to-mouse)
 * 2. Deep Forest Gradient (radial, "Licht aus dem Tal")
 * 3. Fireflies (80-120 Partikel, 2 Größen, warm-grün + warm-amber)
 * 
 * Performance: requestAnimationFrame mit visibilityState-Check
 */
export default function LivingForest() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: 0, y: 0 })
  const animationRef = useRef<number>(0)
  const [visibility, setVisibility] = useState(true)

  // Track mouse for parallax (debounced)
  const handleMouseMove = useCallback((e: MouseEvent) => {
    mouseRef.current.x = (e.clientX / window.innerWidth - 0.5) * 2 // -1 to 1
    mouseRef.current.y = (e.clientY / window.innerHeight - 0.5) * 2
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d', { alpha: false }) // optimize: no alpha on canvas itself
    if (!ctx) return

    let dpr = window.devicePixelRatio || 1
    let W = window.innerWidth
    let H = window.innerHeight
    let particles: Array<{
      x: number
      y: number
      size: number
      speedX: number
      speedY: number
      baseAlpha: number
      pulseSpeed: number
      pulseOffset: number
      colorType: 'green' | 'amber' // warm-green or warm-amber
    }> = []
    let fogBlobs: Array<{
      x: number
      y: number
      radius: number
      vx: number
      vy: number
      phase: number // for slow oscillation
    }> = []

    const resize = () => {
      dpr = window.devicePixelRatio || 1
      W = window.innerWidth
      H = window.innerHeight
      canvas.width = W * dpr
      canvas.height = H * dpr
      canvas.style.width = `${W}px`
      canvas.style.height = `${H}px`
      ctx.scale(dpr, dpr)
    }

    const init = () => {
      resize()

      // Init particles (fireflies)
      const count = Math.min(Math.floor((W * H) / 8000), 120) // cap at 120
      particles = []
      for (let i = 0; i < count; i++) {
        const isAmber = Math.random() < 0.3 // 30% amber
        particles.push({
          x: Math.random() * W,
          y: Math.random() * H,
          size: isAmber ? 1.5 + Math.random() * 1.5 : 3 + Math.random() * 3, // Core: 2-3, Glow: 6-9
          speedX: (Math.random() - 0.5) * 0.4,
          speedY: -Math.random() * 0.3 - 0.05, // slight upward drift
          baseAlpha: 0.3 + Math.random() * 0.5,
          pulseSpeed: 0.01 + Math.random() * 0.02,
          pulseOffset: Math.random() * Math.PI * 2,
          colorType: isAmber ? 'amber' : 'green',
        })
      }

      // Init fog blobs
      fogBlobs = [
        { x: W * 0.2, y: H * 0.3, radius: W * 0.4, vx: 0.0003, vy: 0.0001, phase: 0 },
        { x: W * 0.7, y: H * 0.5, radius: W * 0.35, vx: -0.0002, vy: 0.0002, phase: 2 },
        { x: W * 0.5, y: H * 0.7, radius: W * 0.3, vx: 0.0004, vy: -0.0001, phase: 4 },
      ]
    }

    const draw = (time: number) => {
      if (!visibility) {
        animationRef.current = requestAnimationFrame(draw)
        return
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0) // reset
      ctx.clearRect(0, 0, W, H)

      // === LAYER 1: Deep Forest Gradient (base) ===
      const forestGrad = ctx.createRadialGradient(W * 0.5, H, 0, W * 0.5, H * 0.5, Math.max(W, H))
      forestGrad.addColorStop(0, 'rgba(0, 20, 8, 0.4)')
      forestGrad.addColorStop(0.3, 'rgba(0, 10, 4, 0.25)')
      forestGrad.addColorStop(0.6, 'rgba(0, 5, 2, 0.15)')
      forestGrad.addColorStop(1, 'rgba(0, 0, 0, 0.3)')
      ctx.fillStyle = forestGrad
      ctx.fillRect(0, 0, W, H)

      // === LAYER 2: Mist / Fog Blobs (parallax-to-mouse) ===
      const mouseParallaxX = mouseRef.current.x * 3 // subtle: max 3px
      const mouseParallaxY = mouseRef.current.y * 3
      for (const blob of fogBlobs) {
        blob.phase += 0.003
        blob.x += blob.vx * Math.cos(blob.phase)
        blob.y += blob.vy * Math.sin(blob.phase)

        // Wrap
        if (blob.x < -blob.radius) blob.x = W + blob.radius
        if (blob.x > W + blob.radius) blob.x = -blob.radius
        if (blob.y < -blob.radius) blob.y = H + blob.radius
        if (blob.y > H + blob.radius) blob.y = -blob.radius

        const fogGrad = ctx.createRadialGradient(
          blob.x + mouseParallaxX,
          blob.y + mouseParallaxY,
          0,
          blob.x + mouseParallaxX,
          blob.y + mouseParallaxY,
          blob.radius
        )
        fogGrad.addColorStop(0, 'rgba(200, 210, 200, 0.015)')
        fogGrad.addColorStop(0.5, 'rgba(200, 210, 200, 0.008)')
        fogGrad.addColorStop(1, 'rgba(200, 210, 200, 0)')
        ctx.fillStyle = fogGrad
        ctx.beginPath()
        ctx.arc(blob.x + mouseParallaxX, blob.y + mouseParallaxY, blob.radius, 0, Math.PI * 2)
        ctx.fill()
      }

      // === LAYER 3: Fireflies ===
      for (const p of particles) {
        const pulse = Math.sin(time * p.pulseSpeed + p.pulseOffset) * 0.4 + 0.6
        const alpha = p.baseAlpha * pulse

        // Glow (large, soft)
        const glowSize = p.size * 4
        const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowSize)
        if (p.colorType === 'green') {
          glow.addColorStop(0, `rgba(34, 197, 94, ${alpha * 0.5})`)
          glow.addColorStop(0.4, `rgba(34, 197, 94, ${alpha * 0.15})`)
          glow.addColorStop(1, 'rgba(34, 197, 94, 0)')
        } else {
          glow.addColorStop(0, `rgba(251, 191, 36, ${alpha * 0.4})`)
          glow.addColorStop(0.4, `rgba(251, 191, 36, ${alpha * 0.12})`)
          glow.addColorStop(1, 'rgba(251, 191, 36, 0)')
        }
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(p.x, p.y, glowSize, 0, Math.PI * 2)
        ctx.fill()

        // Core (small, bright)
        const coreColor = p.colorType === 'green' ? 'rgba(134, 239, 172,' : 'rgba(253, 224, 71,'
        ctx.fillStyle = `${coreColor} ${alpha})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()

        // Move
        p.x += p.speedX + mouseRef.current.x * 0.1 // parallax to mouse
        p.y += p.speedY
        p.x += Math.sin(time * 0.001 + p.pulseOffset) * 0.05 // gentle sway

        // Wrap
        if (p.x < -20) p.x = W + 20
        if (p.x > W + 20) p.x = -20
        if (p.y < -20) p.y = H + 20
        if (p.y > H + 20) p.y = -20
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    init()
    animationRef.current = requestAnimationFrame(draw)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      cancelAnimationFrame(animationRef.current)
    }
  }, [visibility, handleMouseMove])

  // Visibility API: pause rendering when tab is hidden
  useEffect(() => {
    const handleVisibility = () => setVisibility(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.85 }}
    />
  )
}