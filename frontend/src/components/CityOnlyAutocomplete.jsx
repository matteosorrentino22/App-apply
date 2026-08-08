import { useEffect, useRef, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { autocompleteCity } from '../api/searches'

const DEBOUNCE_MS = 350

// Variante a campo unico di CityAutocomplete: usata dove serve solo la
// città (esperienze/istruzione del profilo, Sprint 34) — il paese non va
// mostrato come campo separato, si deduce dalla selezione del suggerimento
// (stesso `country_code` derivato da Nominatim).
export default function CityOnlyAutocomplete({ city, onChange, cityId, label, required = false }) {
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const debounceRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleCityChange(value) {
    onChange({ city: value })
    clearTimeout(debounceRef.current)
    if (value.trim().length < 2) {
      setSuggestions([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await autocompleteCity(value)
        setSuggestions(results)
        setOpen(results.length > 0)
      } catch {
        setSuggestions([])
      }
    }, DEBOUNCE_MS)
  }

  function handleSelect(suggestion) {
    onChange({ city: suggestion.city, country: suggestion.country, countryCode: suggestion.country_code })
    setSuggestions([])
    setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative flex min-w-40 flex-1 flex-col gap-1.5">
      <Label htmlFor={cityId}>{label}</Label>
      <Input
        id={cityId}
        value={city}
        autoComplete="off"
        onChange={(e) => handleCityChange(e.target.value)}
        onFocus={() => setOpen(suggestions.length > 0)}
        required={required}
      />
      {open && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md border border-border bg-card shadow-md">
          {suggestions.map((suggestion, index) => (
            <li key={`${suggestion.city}-${suggestion.country}-${index}`}>
              <button
                type="button"
                className="flex w-full flex-col px-3 py-2 text-left text-sm hover:bg-secondary"
                onClick={() => handleSelect(suggestion)}
              >
                <span className="font-medium text-foreground">{suggestion.city}</span>
                <span className="text-xs text-muted-foreground">{suggestion.country}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
