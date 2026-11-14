import * as DialogPrimitive from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'
import { DialogOverlay } from './dialog'

// Finestra centrale per conferme e salvataggi brevi (DESIGN.md §2: salva
// filtri, elimina, esci, conferma di un costo, annulla candidatura, bozza
// superata). Struttura dei mockup (`save-filter`, `confirm-cost`): titolo,
// testo, corpo, azioni impilate a tutta larghezza (primaria sopra,
// "Annulla" testuale sotto). Nessun ✕: si chiude con le azioni o con Esc.
const Modal = DialogPrimitive.Root
const ModalTrigger = DialogPrimitive.Trigger
const ModalClose = DialogPrimitive.Close

function ModalContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        aria-modal="true"
        className={cn(
          'app-modal fixed left-1/2 top-1/2 z-50 w-[calc(100%-40px)] max-w-[420px] -translate-x-1/2 -translate-y-1/2',
          'flex max-h-[90dvh] flex-col gap-3.5 overflow-y-auto rounded-modal bg-card p-5 text-card-foreground shadow-modal outline-none',
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

function ModalTitle({ className, ...props }) {
  return (
    <DialogPrimitive.Title
      className={cn('text-xl font-bold tracking-[-0.01em] text-foreground', className)}
      {...props}
    />
  )
}

function ModalDescription({ className, ...props }) {
  return (
    <DialogPrimitive.Description
      className={cn('text-sm leading-normal text-muted-foreground', className)}
      {...props}
    />
  )
}

function ModalActions({ className, ...props }) {
  return <div className={cn('flex flex-col gap-2 pt-1', className)} {...props} />
}

export { Modal, ModalTrigger, ModalClose, ModalContent, ModalTitle, ModalDescription, ModalActions }
