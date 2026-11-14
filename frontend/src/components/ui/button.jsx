import { Slot } from '@radix-ui/react-slot'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// Altezza minima, non fissa (DESIGN.md §3.6): un'etichetta lunga in
// italiano va a capo invece di uscire dal bottone. Bersagli ≥ 44 px salvo
// `sm`, riservata ad azioni secondarie dentro righe e card.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-button text-center font-semibold leading-tight transition-colors disabled:pointer-events-none disabled:opacity-45 outline-none focus-visible:ring-3 focus-visible:ring-ring/30 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'border border-input bg-card text-primary hover:bg-tint',
        ghost: 'text-foreground hover:bg-secondary',
        text: 'text-primary hover:bg-tint',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      },
      size: {
        default: 'min-h-11 px-4 py-2 text-[15px]',
        sm: 'min-h-9 rounded-field px-3 py-1.5 text-[13px]',
        lg: 'min-h-[52px] w-full px-5 py-3 text-base font-bold',
        icon: 'h-11 w-11',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'default',
    },
  },
)

function Button({ className, variant, size, asChild = false, ...props }) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />
}

export { Button, buttonVariants }
