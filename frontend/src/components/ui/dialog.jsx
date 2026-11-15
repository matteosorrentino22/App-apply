import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useLanguage } from '@/i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Base comune di Modal (finestra centrale) e Sheet (pannello dal basso):
// Radix Dialog gestisce focus, Esc, scroll bloccato e role="dialog".
// Sprint 80: tolti Dialog/DialogContent/... (shadcn), non più usati dopo
// il passaggio di tutte le finestre a Modal e Sheet (Sprint 74–79).
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

export { DialogOverlay, DialogCloseButton }
