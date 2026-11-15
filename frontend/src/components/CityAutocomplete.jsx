import { useEffect, useRef, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLanguage } from '../i18n/LanguageContext'
import { autocompleteCity } from '../api/searches'

const DEBOUNCE_MS = 350

export default function CityAutocomplete({ city, country, onChange, cityId, countryId }) {
  const { t } = useLanguage()
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
    onChange({ city: value, country })
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
    // Sprint 81: città e paese affiancati solo se il contenitore è largo
    // almeno 20rem; prima due minimi da 128 px uscivano dai riquadri stretti.
    <div ref={containerRef} className="@container w-full min-w-0">
      <div className="grid grid-cols-1 gap-4 @[20rem]:grid-cols-2 @[20rem]:gap-3">
      <div className="relative flex min-w-0 flex-col gap-1.5">
        <Label htmlFor={cityId}>{t('onboarding.searchCity')}</Label>
        <Input
          id={cityId}
          value={city}
          autoComplete="off"
          onChange={(e) => handleCityChange(e.target.value)}
          onFocus={() => setOpen(suggestions.length > 0)}
          required
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
      <div className="flex min-w-0 flex-col gap-1.5">
        <Label htmlFor={countryId}>{t('onboarding.searchCountry')}</Label>
        <Input
          id={countryId}
          value={country}
          autoComplete="off"
          onChange={(e) => onChange({ city, country: e.target.value })}
          required
        />
      </div>
      </div>
    </div>
  )
}
