import { useEffect, useRef, useState } from 'react'
import { useLanguage } from '@/i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Testo troncato a `lines` righe con "Leggi tutto" / "Mostra meno" (Sprint
// 75, mockup `detail-nuovo`: "Perché questo punteggio"). Il pulsante compare
// solo se il testo è davvero più lungo (misurato, anche al ridimensionamento).
const CLAMP = { 3: 'line-clamp-3', 4: 'line-clamp-4' }

function ExpandableText({ text, lines = 3, className }) {
  const { t } = useLanguage()
  const ref = useRef(null)
  const [expanded, setExpanded] = useState(false)
  const [overflows, setOverflows] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node || expanded) return
    const measure = () => setOverflows(node.scrollHeight > node.clientHeight + 1)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [text, expanded])

  return (
    <div className="flex flex-col items-start gap-2">
      <p ref={ref} className={cn('whitespace-pre-line break-words', !expanded && CLAMP[lines], className)}>
        {text}
      </p>
      {overflows || expanded ? (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
          className="-mx-1 min-h-9 rounded-field px-1 text-[15px] font-bold text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/30"
        >
          {expanded ? t('jobs.readLess') : t('jobs.readMore')}
        </button>
      ) : null}
    </div>
  )
}

export { ExpandableText }
