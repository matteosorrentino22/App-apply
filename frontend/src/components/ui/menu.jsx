import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

// Menu a tendina senza dipendenze (DESIGN.md §6 `Menu`, mockup `detail-menu`):
// pattern WAI-ARIA "menu button". Il pulsante ha aria-haspopup/aria-expanded;
// il menu si apre con clic, Invio, Spazio o ↓ (primo elemento) / ↑ (ultimo);
// dentro: ↑ ↓ Home Fine per spostarsi, Invio/Spazio per scegliere, Esc per
// chiudere tornando al pulsante; Tab o un clic fuori lo chiudono.
//
//   <Menu label="Altre azioni" side="bottom" items={[{ key, label, icon, onSelect, disabled }]}
//     trigger={(props) => <button {...props}>⋯</button>} />
//
// `side`: 'bottom' (sotto il pulsante) o 'top' (sopra, per la barra in basso).
// Allineato al bordo destro del contenitore (`align="end"`) o sinistro.
function Menu({ label, items, trigger, side = 'bottom', align = 'end', className, menuClassName }) {
  const [open, setOpen] = useState(false)
  const menuId = useId()
  const triggerRef = useRef(null)
  const itemRefs = useRef([])
  const containerRef = useRef(null)
  const pendingFocus = useRef(null)

  const enabled = items.map((item, index) => (item.disabled ? -1 : index)).filter((index) => index >= 0)

  const focusItem = useCallback((index) => {
    itemRefs.current[index]?.focus()
  }, [])

  const close = useCallback((returnFocus = true) => {
    setOpen(false)
    if (returnFocus) triggerRef.current?.focus()
  }, [])

  function openMenu(focus = 'first') {
    pendingFocus.current = focus
    setOpen(true)
  }

  useEffect(() => {
    if (!open) return
    const target = pendingFocus.current === 'last' ? enabled.at(-1) : enabled[0]
    if (target !== undefined) focusItem(target)
    function handlePointer(event) {
      if (!containerRef.current?.contains(event.target)) close(false)
    }
    document.addEventListener('pointerdown', handlePointer)
    return () => document.removeEventListener('pointerdown', handlePointer)
    // Solo all'apertura: `enabled` cambia identità a ogni render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  function handleTriggerKeyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      openMenu('first')
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      openMenu('last')
    }
  }

  function handleMenuKeyDown(event) {
    const current = enabled.indexOf(itemRefs.current.indexOf(document.activeElement))
    const move = (position) => {
      event.preventDefault()
      focusItem(enabled[(position + enabled.length) % enabled.length])
    }
    if (event.key === 'ArrowDown') move(current + 1)
    else if (event.key === 'ArrowUp') move(current < 0 ? enabled.length - 1 : current - 1)
    else if (event.key === 'Home') move(0)
    else if (event.key === 'End') move(enabled.length - 1)
    else if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close()
    } else if (event.key === 'Tab') close(false)
  }

  function select(item) {
    close()
    item.onSelect()
  }

  const triggerProps = {
    ref: triggerRef,
    type: 'button',
    'aria-haspopup': 'menu',
    'aria-expanded': open,
    'aria-controls': open ? menuId : undefined,
    onClick: () => (open ? close() : openMenu('first')),
    onKeyDown: handleTriggerKeyDown,
  }

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {trigger(triggerProps, open)}
      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={handleMenuKeyDown}
          className={cn(
            'absolute z-40 flex w-max min-w-[220px] max-w-[calc(100vw-32px)] flex-col rounded-card border border-border bg-card p-1.5 shadow-popover',
            side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2',
            align === 'end' ? 'right-0' : 'left-0',
            menuClassName,
          )}
        >
          {items.map((item, index) => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                ref={(element) => {
                  itemRefs.current[index] = element
                }}
                type="button"
                role="menuitem"
                tabIndex={-1}
                disabled={item.disabled}
                onClick={() => select(item)}
                className={cn(
                  'flex min-h-11 items-center gap-3 rounded-field px-3 py-2 text-left text-base font-semibold outline-none transition-colors',
                  'hover:bg-tint focus-visible:bg-tint focus:bg-tint disabled:pointer-events-none disabled:opacity-45',
                  item.destructive ? 'text-destructive-text' : 'text-foreground',
                )}
              >
                {Icon ? <Icon className="h-5 w-5 shrink-0 text-chip-foreground" aria-hidden="true" /> : null}
                <span>{item.label}</span>
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

export { Menu }
