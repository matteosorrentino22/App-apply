import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../i18n/LanguageContext'

// Attività di un ruolo come chip modificabili (Sprint 82, SPEC-DELTA A15,
// mockup `profile-act-chip`, `profile-act-modifica`, `profile-act-errore`,
// `profile-act-limite`, `profile-act-vuoto`, `desk-profile-act`). Stessi dati
// di prima (lista di stringhe) e stessi limiti (15 per ruolo, 400 caratteri):
// - chip ad angoli ridotti, testo troncato a 3 righe;
// - tocco sul testo = modifica in un riquadro con contatore, Annulla / Fatto
//   (Fatto disattivato oltre il limite); ✕ con area da 44 px = elimina;
// - campo in fondo per aggiungere (Invio), bloccato a 15 attività.
// Le tecnologie restano su `ChipInput` (decisione del committente).
export default function ActivityChipsInput({
  id,
  value,
  onChange,
  placeholder,
  maxLength = 400,
  maxItems = 15,
  flagTooLong = false,
  describedBy,
}) {
  const { t } = useLanguage()
  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState(null) // { index, text }
  const editRef = useRef(null)
  const full = value.length >= maxItems
  const editIndex = editing ? editing.index : null
  const editText = editing ? editing.text : null

  useEffect(() => {
    if (editIndex !== null && editRef.current) {
      const el = editRef.current
      el.focus()
      el.setSelectionRange(el.value.length, el.value.length)
    }
  }, [editIndex])

  // Altezza del riquadro di modifica = altezza del testo.
  useEffect(() => {
    if (editRef.current) {
      editRef.current.style.height = 'auto'
      editRef.current.style.height = `${editRef.current.scrollHeight}px`
    }
  }, [editText])

  function commitDraft() {
    const next = draft.trim()
    if (!next || full) return
    onChange([...value, next])
    setDraft('')
  }

  function removeAt(index) {
    if (editing?.index === index) setEditing(null)
    onChange(value.filter((_, i) => i !== index))
  }

  const editTooLong = editing ? editing.text.length > maxLength : false
  const editEmpty = editing ? !editing.text.trim() : false

  function confirmEdit() {
    if (!editing || editTooLong || editEmpty) return
    onChange(value.map((item, i) => (i === editing.index ? editing.text.trim() : item)))
    setEditing(null)
  }

  return (
    <div className="flex min-w-0 flex-col gap-2">
      {value.length === 0 ? <p className="text-[15px] text-muted-foreground">{t('profileExtras.activitiesEmpty')}</p> : null}

      {value.map((item, index) =>
        editing?.index === index ? (
          <div key={`edit-${index}`} className="flex flex-col gap-1.5">
            <div
              className={cn(
                'flex flex-col gap-2 rounded-field border bg-card px-3.5 pb-2.5 pt-3 has-[textarea:focus]:ring-3',
                editTooLong ? 'border-destructive has-[textarea:focus]:ring-destructive/20' : 'border-ring has-[textarea:focus]:ring-ring/20',
              )}
            >
              <textarea
                ref={editRef}
                rows={2}
                value={editing.text}
                aria-label={t('profileExtras.activityEditLabel')}
                aria-invalid={editTooLong || undefined}
                aria-describedby={editTooLong ? `${id}-edit-error` : undefined}
                onChange={(event) => setEditing({ index, text: event.target.value })}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') {
                    event.preventDefault()
                    setEditing(null)
                  } else if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    confirmEdit()
                  }
                }}
                className="w-full resize-none overflow-hidden border-none bg-transparent p-0 text-base leading-normal text-foreground outline-none"
              />
              <div className="flex items-center justify-between gap-2">
                <span className={cn('text-[13px] tabular-nums', editTooLong ? 'font-bold text-destructive-text' : 'text-muted-foreground')}>
                  {editing.text.length} / {maxLength}
                </span>
                <div className="flex items-center gap-1">
                  <Button type="button" variant="text" onClick={() => setEditing(null)}>
                    {t('common.cancel')}
                  </Button>
                  <Button type="button" onClick={confirmEdit} disabled={editTooLong || editEmpty}>
                    {t('profileExtras.activityDone')}
                  </Button>
                </div>
              </div>
            </div>
            {editTooLong ? (
              <p id={`${id}-edit-error`} role="alert" className="text-[13px] leading-snug text-destructive-text">
                {t('profileExtras.activityTooLong').replace('{length}', maxLength)}
              </p>
            ) : null}
          </div>
        ) : (
          <div
            key={`${item}-${index}`}
            className={cn(
              'flex min-w-0 items-start rounded-[10px] bg-primary-soft text-foreground',
              flagTooLong && item.length > maxLength && 'bg-destructive-soft text-destructive-text',
            )}
            data-testid="activity-chip"
          >
            <button
              type="button"
              onClick={() => setEditing({ index, text: item })}
              aria-label={t('profileExtras.activityEdit').replace('{text}', item)}
              className="min-h-11 min-w-0 flex-1 rounded-[10px] px-3.5 py-2.5 text-left text-[15px] leading-snug outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
            >
              <span className="line-clamp-3 [overflow-wrap:anywhere]">{item}</span>
            </button>
            <button
              type="button"
              onClick={() => removeAt(index)}
              aria-label={t('common.removeItem').replace('{item}', item)}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] text-chip-foreground outline-none hover:bg-primary/10 focus-visible:ring-3 focus-visible:ring-ring/30"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ),
      )}

      <input
        id={id}
        type="text"
        value={draft}
        maxLength={maxLength}
        disabled={full}
        aria-describedby={describedBy}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault()
            commitDraft()
          }
        }}
        onBlur={commitDraft}
        placeholder={full ? t('profileExtras.activitiesMaxReached').replace('{max}', maxItems) : placeholder}
        className="flex h-12 w-full min-w-0 rounded-field border border-input bg-card px-3.5 text-base text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:bg-secondary disabled:placeholder:text-chip-foreground"
      />
    </div>
  )
}
