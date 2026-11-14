import { Children, cloneElement, isValidElement, useId } from 'react'
import { cn } from '@/lib/utils'
import { Label } from './label'

// Etichetta + controllo + suggerimento/errore (DESIGN.md §6, mockup
// `add-manual`, `detail-gap`). Collega da solo id, aria-describedby e
// aria-invalid al controllo figlio (Input, Textarea, SelectTrigger, ...).
function Field({ label, hint, error, id, className, children }) {
  const autoId = useId()
  const controlId = id || autoId
  const hintId = hint ? `${controlId}-hint` : undefined
  const errorId = error ? `${controlId}-error` : undefined
  const describedBy = [errorId, hintId].filter(Boolean).join(' ') || undefined

  const child = Children.only(children)
  const control = isValidElement(child)
    ? cloneElement(child, {
        id: child.props.id || controlId,
        'aria-describedby': [child.props['aria-describedby'], describedBy].filter(Boolean).join(' ') || undefined,
        'aria-invalid': error ? true : child.props['aria-invalid'],
      })
    : child

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label ? <Label htmlFor={child.props?.id || controlId}>{label}</Label> : null}
      {control}
      {error ? (
        <p id={errorId} className="text-xs leading-snug text-destructive-text">
          {error}
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="text-xs leading-snug text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

export { Field }
