import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

let nextKey = 0
function makeKey() {
  nextKey += 1
  return `row-${nextKey}`
}

export function emptyRow(fields) {
  const row = { _key: makeKey() }
  for (const field of fields) {
    row[field.name] = ''
  }
  return row
}

/**
 * Editor generico per le sezioni ripetibili a campi di testo semplici
 * (istruzione, competenze, certificazioni, lingue): stessa struttura
 * aggiungi/rimuovi riga, config diversa per sezione — evita di duplicare
 * quattro volte la stessa logica di gestione lista. Le esperienze hanno un
 * editor dedicato (ExperienceGroupEditor) perché vanno raggruppate per
 * azienda, non trattate come righe indipendenti.
 *
 * `field.options` (array `{value, label}`) rende un menu a tendina invece
 * del testo libero — usato per lingua/livello (Sprint 41: valori fissi,
 * non più testo libero disomogeneo).
 */
export default function ListSectionEditor({ title, addLabel, fields, rows, onChange, removeLabel }) {
  function updateRow(key, fieldName, value) {
    onChange(rows.map((row) => (row._key === key ? { ...row, [fieldName]: value } : row)))
  }

  function addRow() {
    onChange([...rows, emptyRow(fields)])
  }

  function removeRow(key) {
    onChange(rows.filter((row) => row._key !== key))
  }

  // Sprint 81: righe in un riquadro leggero, campi a tutta larghezza
  // (affiancati da 22rem di contenitore se più d'uno, es. lingua e
  // livello), "Rimuovi" come pulsante di testo da 44 px.
  return (
    <fieldset className="flex min-w-0 flex-col gap-4">
      <legend className="mb-1 text-base font-semibold text-foreground">{title}</legend>
      {rows.map((row) => (
        <div key={row._key} className="@container flex min-w-0 flex-col gap-2 rounded-field border border-border bg-tint p-3 sm:p-4" data-testid="list-row">
          <div className={fields.length > 1 ? 'grid grid-cols-1 gap-4 @[22rem]:grid-cols-2 @[22rem]:gap-3' : 'flex flex-col'}>
            {fields.map((field) => (
              <div key={field.name} className="flex min-w-0 flex-col gap-1.5">
                <Label htmlFor={`${row._key}-${field.name}`}>
                  {field.label}
                  {field.required && ' *'}
                </Label>
                {field.options ? (
                  <Select
                    value={row[field.name] || undefined}
                    onValueChange={(value) => updateRow(row._key, field.name, value)}
                  >
                    <SelectTrigger id={`${row._key}-${field.name}`} aria-label={field.label} className="w-full min-w-0">
                      <SelectValue placeholder={field.label} />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id={`${row._key}-${field.name}`}
                    type={field.type || 'text'}
                    required={field.required}
                    value={row[field.name] || ''}
                    onChange={(event) => updateRow(row._key, field.name, event.target.value)}
                  />
                )}
              </div>
            ))}
          </div>
          <Button
            type="button"
            variant="text"
            onClick={() => removeRow(row._key)}
            className="-ml-2 self-start px-2 text-destructive-text hover:bg-destructive-soft"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {removeLabel}
          </Button>
        </div>
      ))}
      <Button type="button" variant="secondary" onClick={addRow} className="w-fit">
        <Plus className="h-4 w-4" aria-hidden="true" />
        {addLabel}
      </Button>
    </fieldset>
  )
}
