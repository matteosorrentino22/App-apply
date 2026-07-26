import { useState } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ChipInput({ value, onChange, placeholder, className, id }) {
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
        'flex flex-wrap items-center gap-1.5 rounded-md border border-input bg-card px-2 py-1.5',
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
          className="inline-flex items-center gap-1 rounded-full bg-primary-soft py-1 pl-3 pr-1 text-[13px] font-medium text-primary"
        >
          {item}
          <button
            type="button"
            aria-label={`Rimuovi ${item}`}
            onClick={() => removeAt(index)}
            className="rounded-full p-0.5 text-primary hover:bg-primary/15"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </span>
      ))}
      <input
        id={id}
        type="text"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        placeholder={value.length === 0 ? placeholder : ''}
        className="min-w-[140px] flex-1 border-none bg-transparent px-1 py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground"
      />
    </div>
  )
}
