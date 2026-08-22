import { Trash2 } from 'lucide-react'
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

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-base font-semibold text-foreground">{title}</legend>
      {rows.map((row) => (
        <div key={row._key} className="flex flex-wrap items-end gap-3 rounded-lg border border-border p-3">
          {fields.map((field) => (
            <div key={field.name} className="flex min-w-40 flex-1 flex-col gap-1.5">
              <Label htmlFor={`${row._key}-${field.name}`}>
                {field.label}
                {field.required && ' *'}
              </Label>
              {field.options ? (
                <Select
                  value={row[field.name] || undefined}
                  onValueChange={(value) => updateRow(row._key, field.name, value)}
                >
                  <SelectTrigger id={`${row._key}-${field.name}`} aria-label={field.label}>
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
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => removeRow(row._key)}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {removeLabel}
          </Button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={addRow} className="w-fit">
        {addLabel}
      </Button>
    </fieldset>
  )
}
