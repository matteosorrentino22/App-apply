import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// Riquadro di avviso (DESIGN.md §5–§6). Varianti dai mockup:
// info (`jobs-avvisi`: profilo incompleto, nuova versione), note (avvisi
// neutri: documento su più pagine, email non verificata), error (errori di
// form), success (email inviata). `action` è un nodo (bottone o link) a
// destra del testo; con testi lunghi va a capo sotto.
const bannerVariants = cva('flex flex-wrap items-center gap-x-3 gap-y-2 rounded-button px-3.5 py-3 text-sm leading-[1.45]', {
  variants: {
    variant: {
      info: 'bg-primary-soft text-primary',
      note: 'border border-note-border bg-note text-note-foreground',
      error: 'border border-destructive-border bg-destructive-soft text-destructive-text',
      success: 'border border-success-border bg-success-soft text-success',
    },
  },
  defaultVariants: { variant: 'info' },
})

function Banner({ variant = 'info', title, icon: Icon, action, className, children, ...props }) {
  return (
    <div role={variant === 'error' ? 'alert' : 'status'} className={cn(bannerVariants({ variant }), className)} {...props}>
      {Icon ? <Icon className="h-[18px] w-[18px] shrink-0 self-start mt-px" aria-hidden="true" /> : null}
      <div className="min-w-0 flex-1 basis-48">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div>{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export { Banner }
