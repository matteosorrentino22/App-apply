import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold',
  {
    variants: {
      variant: {
        primary: 'bg-primary-soft text-primary',
        neutral: 'bg-accent text-muted-foreground',
      },
    },
    defaultVariants: {
      variant: 'primary',
    },
  },
)

function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />
}

export { Badge, badgeVariants }
