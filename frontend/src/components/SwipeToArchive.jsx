import { useRef, useState } from 'react'
import { Archive } from 'lucide-react'

const THRESHOLD = 88

// Swipe verso sinistra per archiviare (pattern standard mobile "swipe to
// delete"), con pointer events (funziona sia a dito sia con drag del mouse,
// utile anche per i test e2e). Resta comunque disponibile un bottone
// esplicito nella card per chi non usa il gesto (tastiera, desktop).
export default function SwipeToArchive({ onSwipe, actionLabel, children }) {
  const [dragX, setDragX] = useState(0)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startY = useRef(0)
  const isHorizontal = useRef(null)

  function handlePointerDown(event) {
    // Un pointerdown che parte da un bottone/link (Dettagli, Archivia,
    // Genera CV...) non deve avviare uno swipe: la pointer capture sotto
    // spezzerebbe il click nativo di quell'elemento.
    if (event.target.closest('button, a')) return

    dragging.current = true
    isHorizontal.current = null
    startX.current = event.clientX
    startY.current = event.clientY
    // Senza pointer capture, se il drag esce dai confini dell'elemento (il
    // caso normale per uno swipe ampio) i successivi pointermove smettono di
    // arrivare qui: il gesto si "perde" a metà.
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function handlePointerMove(event) {
    if (!dragging.current) return
    const dx = event.clientX - startX.current
    const dy = event.clientY - startY.current
    if (isHorizontal.current === null) {
      if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return
      isHorizontal.current = Math.abs(dx) > Math.abs(dy)
    }
    if (!isHorizontal.current) return
    event.preventDefault()
    setDragX(Math.min(0, dx))
  }

  function endDrag(event) {
    if (!dragging.current) return
    dragging.current = false
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    if (Math.abs(dragX) > THRESHOLD) {
      onSwipe()
    }
    setDragX(0)
    isHorizontal.current = null
  }

  const revealWidth = Math.min(Math.abs(dragX), 160)

  return (
    <div className="relative overflow-hidden rounded-xl" data-testid="swipe-row">
      <div
        className="absolute inset-y-0 right-0 flex items-center justify-end gap-2 rounded-xl bg-destructive px-5 text-sm font-medium text-destructive-foreground"
        style={{ width: revealWidth }}
        aria-hidden="true"
      >
        {revealWidth > 48 && (
          <>
            <Archive className="h-4 w-4 shrink-0" />
            <span className="whitespace-nowrap">{actionLabel}</span>
          </>
        )}
      </div>
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        style={{
          transform: `translateX(${dragX}px)`,
          transition: dragging.current ? 'none' : 'transform 150ms ease',
          touchAction: 'pan-y',
        }}
        className="relative"
      >
        {children}
      </div>
    </div>
  )
}
