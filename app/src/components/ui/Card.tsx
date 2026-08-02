import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, hover = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'liquid-glass rounded-2xl p-6 transition-all duration-300',
        hover && 'hover:bg-green-500/5 hover:border-green-500/20 hover:forest-glow cursor-pointer',
        className,
      )}
      {...props}
    />
  ),
)
Card.displayName = 'Card'

export { Card }
