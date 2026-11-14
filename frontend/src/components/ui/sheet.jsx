import * as DialogPrimitive from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'
import { DialogCloseButton, DialogOverlay } from './dialog'

// Pannello dal basso (DESIGN.md §2): filtri, raccolta, generazione, nuova
// ricerca, assistente AI su mobile, inserimento manuale. Struttura del
// mockup `detail-gap`: maniglia, titolo con ✕, corpo scorrevole, piede
// fisso con bordo superiore e area sicura iOS. Da 1024 px diventa una
// finestra centrale larga 480 px con lo stesso contenuto.
const Sheet = DialogPrimitive.Root
const SheetTrigger = DialogPrimitive.Trigger
const SheetClose = DialogPrimitive.Close

function SheetContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        aria-modal="true"
        className={cn(
          'app-sheet fixed inset-x-0 bottom-0 z-50 flex max-h-[92dvh] flex-col overflow-hidden',
          'rounded-t-sheet bg-card text-card-foreground shadow-modal outline-none',
          'lg:inset-x-auto lg:bottom-auto lg:left-1/2 lg:top-1/2 lg:max-h-[85dvh] lg:w-[480px] lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-modal',
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

// Maniglia + titolo + ✕. `description` facoltativa sotto il titolo.
function SheetHeader({ title, description, className }) {
  return (
    <div className={cn('flex flex-none flex-col gap-3 px-4 pt-2.5 lg:px-5 lg:pt-4', className)}>
      <div aria-hidden="true" className="h-1 w-10 self-center rounded-full bg-grabber lg:hidden" />
      <div className="flex items-center justify-between gap-3">
        <DialogPrimitive.Title className="min-w-0 text-xl font-bold tracking-[-0.01em] text-foreground">
          {title}
        </DialogPrimitive.Title>
        <DialogCloseButton className="-mr-2.5" />
      </div>
      {description ? (
        <DialogPrimitive.Description className="text-sm leading-normal text-muted-foreground">
          {description}
        </DialogPrimitive.Description>
      ) : null}
    </div>
  )
}

function SheetBody({ className, ...props }) {
  return (
    <div
      className={cn('flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4 pt-1 lg:px-5', className)}
      {...props}
    />
  )
}

// Piede fisso: azioni impilate, padding inferiore con l'area sicura iOS.
function SheetFooter({ className, ...props }) {
  return (
    <div
      className={cn(
        'flex flex-none flex-col gap-2 border-t border-border px-4 pt-3 pb-[max(28px,calc(12px_+_env(safe-area-inset-bottom)))] lg:px-5 lg:pb-5',
        className,
      )}
      {...props}
    />
  )
}

export { Sheet, SheetTrigger, SheetClose, SheetContent, SheetHeader, SheetBody, SheetFooter }
