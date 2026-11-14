import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex w-fit items-center whitespace-nowrap rounded-full px-2.5 py-[3px] text-[11px] font-semibold',
  {
    variants: {
      variant: {
        primary: 'bg-primary-soft text-primary',
        neutral: 'bg-chip text-chip-foreground',
        success: 'bg-success-soft text-success',
        destructive: 'bg-destructive-soft text-destructive-text',
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
