import { useRef, useState } from 'react'
import { Archive } from 'lucide-react'

const THRESHOLD = 88

// Swipe verso sinistra per archiviare (pattern standard mobile "swipe to
// delete"), con pointer events (funziona sia a dito sia con drag del mouse,
// utile anche per i test e2e).
//
// Dallo Sprint 74 la card è tutta cliccabile (link "stirato" sul titolo,
// marcato `data-card-link`): il gesto può partire anche da lì. Per non
// rompere il tocco semplice sul link, la pointer capture si prende solo
// quando il movimento è davvero orizzontale; dopo uno swipe il click che il
// browser genera al rilascio viene annullato, così non si apre il dettaglio.
// Bottoni e altri link (cuoricino, profilo del recruiter) non avviano lo swipe.
export default function SwipeToArchive({ onSwipe, actionLabel, children }) {
  const [dragX, setDragX] = useState(0)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startY = useRef(0)
  const isHorizontal = useRef(null)
  const suppressClick = useRef(false)

  function handlePointerDown(event) {
    if (event.target.closest('button, a:not([data-card-link])')) return
    dragging.current = true
    isHorizontal.current = null
    suppressClick.current = false
    startX.current = event.clientX
    startY.current = event.clientY
  }

  function handlePointerMove(event) {
    if (!dragging.current) return
    const dx = event.clientX - startX.current
    const dy = event.clientY - startY.current
    if (isHorizontal.current === null) {
      if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return
      isHorizontal.current = Math.abs(dx) > Math.abs(dy)
      if (isHorizontal.current) {
        suppressClick.current = true
        // Senza pointer capture, se il drag esce dai confini dell'elemento (il
        // caso normale per uno swipe ampio) i successivi pointermove smettono
        // di arrivare qui: il gesto si "perde" a metà.
        event.currentTarget.setPointerCapture(event.pointerId)
      }
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

  function handleClickCapture(event) {
    if (!suppressClick.current) return
    suppressClick.current = false
    event.preventDefault()
    event.stopPropagation()
  }

  const revealWidth = Math.min(Math.abs(dragX), 160)

  return (
    <div className="relative overflow-hidden rounded-card" data-testid="swipe-row">
      <div
        className="absolute inset-y-0 right-0 flex items-center justify-end gap-2 rounded-card bg-destructive px-5 text-sm font-semibold text-destructive-foreground"
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
        onClickCapture={handleClickCapture}
        onDragStart={(event) => event.preventDefault()}
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
