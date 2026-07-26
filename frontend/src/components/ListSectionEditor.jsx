let nextKey = 0
function makeKey() {
  nextKey += 1
  return `row-${nextKey}`
}

export function emptyRow(fields) {
  const row = { _key: makeKey() }
  for (const field of fields) {
    row[field.name] = field.type === 'lines' ? [] : ''
  }
  return row
}

/**
 * Editor generico per le sezioni ripetibili del profilo (esperienze,
 * istruzione, competenze, certificazioni, lingue): stessa struttura
 * (aggiungi/rimuovi righe, campi testo o "una voce per riga"), config
 * diversa per sezione — evita di duplicare cinque volte la stessa logica
 * di gestione lista.
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
    <fieldset className="list-section">
      <legend>{title}</legend>
      {rows.map((row) => (
        <div className="list-section-row" key={row._key}>
          {fields.map((field) =>
            field.type === 'lines' ? (
              <label key={field.name}>
                {field.label}
                <textarea
                  value={(row[field.name] || []).join('\n')}
                  onChange={(event) =>
                    updateRow(
                      row._key,
                      field.name,
                      event.target.value.split('\n').filter((line) => line.trim() !== ''),
                    )
                  }
                />
              </label>
            ) : (
              <label key={field.name}>
                {field.label}
                <input
                  type="text"
                  value={row[field.name] || ''}
                  onChange={(event) => updateRow(row._key, field.name, event.target.value)}
                />
              </label>
            ),
          )}
          <button type="button" onClick={() => removeRow(row._key)}>
            {removeLabel}
          </button>
        </div>
      ))}
      <button type="button" onClick={addRow}>
        {addLabel}
      </button>
    </fieldset>
  )
}
