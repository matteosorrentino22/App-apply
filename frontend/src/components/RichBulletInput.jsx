import { useEffect, useRef } from 'react'
import { Bold } from 'lucide-react'
import { cn } from '@/lib/utils'

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function markersToHtml(text) {
  return escapeHtml(text || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}

function nodeToMarkers(node) {
  let result = ''
  node.childNodes.forEach((child) => {
    if (child.nodeType === Node.TEXT_NODE) {
      result += child.textContent
      return
    }
    if (child.nodeType !== Node.ELEMENT_NODE) return
    const tag = child.tagName.toLowerCase()
    if (tag === 'br') return
    const inner = nodeToMarkers(child)
    result += tag === 'strong' || tag === 'b' ? (inner ? `**${inner}**` : '') : inner
  })
  return result
}

function nearestStrong(node, container) {
  let el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node
  while (el && el !== container) {
    if (el.tagName === 'STRONG') return el
    el = el.parentElement
  }
  return null
}

function unwrap(el) {
  const parent = el.parentNode
  while (el.firstChild) parent.insertBefore(el.firstChild, el)
  parent.removeChild(el)
}

// Grassetto "alla Word" sui bullet del CV (Sprint 58): selezioni il testo
// nel campo e premi il pulsante/Ctrl+B, invece di gestire una lista
// separata di parole chiave. Sotto, il valore resta una stringa semplice
// con marcatori "**parola**" — lo stesso formato che Claude usa già
// direttamente nei bullet generati (vedi ai_content.py) — così grassetto
// automatico e manuale finiscono nello stesso identico campo "text", letto
// dallo stesso filtro di rendering (templatetags/cv_extras.py) sia nel PDF
// finale sia nella preview live dell'editor.
export default function RichBulletInput({ value, onChange, className }) {
  const ref = useRef(null)
  const focusedRef = useRef(false)

  useEffect(() => {
    if (!ref.current || focusedRef.current) return
    ref.current.innerHTML = markersToHtml(value)
  }, [value])

  function syncToState() {
    if (ref.current) onChange(nodeToMarkers(ref.current))
  }

  function toggleBold() {
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return
    const range = selection.getRangeAt(0)
    if (!ref.current.contains(range.commonAncestorContainer)) return

    const startStrong = nearestStrong(range.startContainer, ref.current)
    const endStrong = nearestStrong(range.endContainer, ref.current)
    if (startStrong && startStrong === endStrong) {
      unwrap(startStrong)
    } else {
      const strong = document.createElement('strong')
      strong.appendChild(range.extractContents())
      range.insertNode(strong)
    }
    syncToState()
  }

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'b') {
      event.preventDefault()
      toggleBold()
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
    }
  }

  function handlePaste(event) {
    event.preventDefault()
    const text = event.clipboardData.getData('text/plain')
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) return
    const range = selection.getRangeAt(0)
    range.deleteContents()
    const textNode = document.createTextNode(text)
    range.insertNode(textNode)
    range.setStartAfter(textNode)
    range.setEndAfter(textNode)
    selection.removeAllRanges()
    selection.addRange(range)
    syncToState()
  }

  return (
    // Sprint 76: solo aspetto (token del redesign, testo a 16 px che evita lo
    // zoom automatico dell'iPhone, pulsante del grassetto da 32 px).
    <div
      className={cn(
        'flex-1 overflow-hidden rounded-field border border-input bg-card transition-[border-color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/20',
        className,
      )}
    >
      <button
        type="button"
        onMouseDown={(event) => event.preventDefault()}
        onClick={toggleBold}
        className="relative m-1 inline-flex h-8 w-8 items-center after:absolute after:content-[''] after:-inset-1.5 justify-center rounded-[8px] text-chip-foreground hover:bg-tint"
        aria-label="Bold"
        title="Bold (Ctrl/Cmd+B)"
      >
        <Bold className="h-4 w-4" />
      </button>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onFocus={() => {
          focusedRef.current = true
        }}
        onBlur={() => {
          focusedRef.current = false
        }}
        onInput={syncToState}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        className="min-h-12 w-full whitespace-pre-wrap px-3.5 pb-3 pt-1 text-base leading-[1.45] text-foreground outline-none"
      />
    </div>
  )
}
