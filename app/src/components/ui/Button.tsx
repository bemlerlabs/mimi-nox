import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef } from 'react'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500/30 disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary: 'bg-green-500 hover:bg-green-600 text-black forest-glow',
        secondary: 'liquid-glass hover:bg-green-500/10 text-white',
        ghost: 'hover:bg-green-500/5 text-white/70 hover:text-white',
        destructive: 'bg-red-600 hover:bg-red-700 text-white',
        link: 'text-green-400 hover:text-green-300 underline underline-offset-4',
      },
      size: {
        sm: 'h-8 px-3 text-xs gap-1.5',
        md: 'h-10 px-4 text-sm gap-2',
        lg: 'h-12 px-6 text-base gap-2.5',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  as?: 'button' | 'a'
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, as: Tag = 'button', ...props }, ref) => {
    return (
      // @ts-expect-error — polymorfer Tag (button | a) mit forwardRef
      <Tag className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
