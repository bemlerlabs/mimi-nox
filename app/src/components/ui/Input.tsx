import { cn } from '@/lib/utils'
import { forwardRef, InputHTMLAttributes } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement>

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        'liquid-glass rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 outline-none transition-all duration-200 focus:border-green-500/30 focus:ring-2 focus:ring-green-500/20 focus:forest-glow-subtle',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

export { Input }
