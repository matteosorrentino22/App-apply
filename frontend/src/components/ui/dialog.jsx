import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useLanguage } from '@/i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Base comune di Modal (finestra centrale) e Sheet (pannello dal basso):
// Radix Dialog gestisce focus, Esc, scroll bloccato e role="dialog".
const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger
const DialogClose = DialogPrimitive.Close

function DialogOverlay({ className, ...props }) {
  return (
    <DialogPrimitive.Overlay
      className={cn('app-overlay fixed inset-0 z-50 bg-overlay', className)}
      {...props}
    />
  )
}

// Pulsante ✕ con bersaglio di 44 px e etichetta tradotta.
function DialogCloseButton({ className }) {
  const { t } = useLanguage()
  return (
    <DialogPrimitive.Close
      aria-label={t('common.close')}
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/30',
        className,
      )}
    >
      <X className="h-[22px] w-[22px]" strokeWidth={2.2} aria-hidden="true" />
    </DialogPrimitive.Close>
  )
}

// Finestra centrale (DESIGN.md §2, §3.3: raggio 20, padding 20, margini 20
// ai lati su mobile). Usata dalle pagine esistenti; il nuovo `Modal` ne
// riprende l'aspetto con le azioni impilate dei mockup.
function DialogContent({ className, children, showClose = true, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        className={cn(
          'app-modal fixed left-1/2 top-1/2 z-50 w-[calc(100%-40px)] max-w-lg -translate-x-1/2 -translate-y-1/2',
          'rounded-modal bg-card p-5 text-card-foreground shadow-modal outline-none',
          'max-h-[90dvh] overflow-y-auto',
          className,
        )}
        {...props}
      >
        {children}
        {showClose && <DialogCloseButton className="absolute right-2.5 top-2.5" />}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

function DialogHeader({ className, ...props }) {
  return <div className={cn('mb-4 flex flex-col gap-1.5 pr-8', className)} {...props} />
}

function DialogTitle({ className, ...props }) {
  return (
    <DialogPrimitive.Title
      className={cn('text-xl font-bold tracking-[-0.01em] text-foreground', className)}
      {...props}
    />
  )
}

function DialogDescription({ className, ...props }) {
  return (
    <DialogPrimitive.Description
      className={cn('text-sm leading-normal text-muted-foreground', className)}
      {...props}
    />
  )
}

function DialogFooter({ className, ...props }) {
  return <div className={cn('mt-5 flex flex-wrap justify-end gap-3', className)} {...props} />
}

export {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogOverlay,
  DialogCloseButton,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
}
