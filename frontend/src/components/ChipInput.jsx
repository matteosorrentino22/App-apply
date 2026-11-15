import { useState } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLanguage } from '../i18n/LanguageContext'

// `maxLength` (Sprint 70) limita il testo di una nuova voce; con
// `flagTooLong` le voci già presenti oltre il limite (es. dal pre-compilamento
// da CV) sono evidenziate, perché il server le rifiuterebbe.
export default function ChipInput({ value, onChange, placeholder, className, id, maxLength, flagTooLong = false }) {
  const { t } = useLanguage()
  const [draft, setDraft] = useState('')

  function commitDraft() {
    const next = draft.trim()
    if (!next) return
    onChange([...value, next])
    setDraft('')
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      commitDraft()
    } else if (event.key === 'Backspace' && draft === '' && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  function removeAt(index) {
    onChange(value.filter((_, i) => i !== index))
  }

  return (
    <div
      className={cn(
        // Sprint 81: alto e arrotondato come gli altri campi, a tutta larghezza.
        'flex min-h-12 w-full min-w-0 flex-wrap items-center gap-1.5 rounded-field border border-input bg-card px-2 py-1.5',
        'has-[input:focus]:border-ring has-[input:focus]:ring-3 has-[input:focus]:ring-ring/20',
        className,
      )}
      onClick={(event) => {
        if (event.currentTarget === event.target) event.currentTarget.querySelector('input')?.focus()
      }}
    >
      {value.map((item, index) => (
        <span
          key={`${item}-${index}`}
          className={cn(
            'inline-flex min-w-0 max-w-full items-center gap-1 rounded-full bg-primary-soft py-1 pl-3 pr-1 text-[13px] font-medium text-primary [overflow-wrap:anywhere]',
            flagTooLong && maxLength && item.length > maxLength && 'bg-destructive-soft text-destructive',
          )}
        >
          {item}
          <button
            type="button"
            aria-label={t('common.removeItem').replace('{item}', item)}
            onClick={() => removeAt(index)}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-primary hover:bg-primary/15"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </span>
      ))}
      <input
        id={id}
        type="text"
        value={draft}
        maxLength={maxLength}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        placeholder={value.length === 0 ? placeholder : ''}
        className="min-w-[120px] flex-1 border-none bg-transparent px-1.5 py-1.5 text-base text-foreground outline-none placeholder:text-muted-foreground"
      />
    </div>
  )
}
