import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, Globe, MapPin, Plus, X } from 'lucide-react'
import { autocompleteCity } from '../api/searches'
import { useLanguage } from '../i18n/LanguageContext'
import { countryCodeFor, countryOptions } from '../utils/countries'
import { Label } from '@/components/ui/label'

const DEBOUNCE_MS = 350

// Paese e città di una ricerca o del lavoro dei desideri (Sprint 84, A17,
// mockup `ricerca-nuova-citta-pro`, `ricerca-nuova-citta-free`,
// `desiderio-pro`): prima il paese (elenco), poi le città come chip (fino a
// `maxCities`); con una sola città (Free) un campo semplice. Suggerimenti
// solo del paese scelto; città e paese salvati in inglese.
export default function CityChipsField({ idPrefix, country, onCountryChange, cities, onCitiesChange, maxCities, hint }) {
  const { t, lang } = useLanguage()
  const options = useMemo(() => countryOptions(lang), [lang])
  const countryCode = countryCodeFor(country)
  const single = maxCities === 1

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${idPrefix}-country`}>{t('searches.country')}</Label>
        <div className="relative">
          <Globe className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <select
            id={`${idPrefix}-country`}
            value={countryCode ? country : ''}
            required
            onChange={(event) => onCountryChange(event.target.value)}
            className="h-12 w-full min-w-0 appearance-none rounded-field border border-input bg-card pl-11 pr-10 text-base text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20"
          >
            <option value="" disabled>
              {t('searches.countryPlaceholder')}
            </option>
            {options.map((option) => (
              <option key={option.code} value={option.name}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <Label htmlFor={`${idPrefix}-city`}>{t('searches.cities')}</Label>
          {single ? null : (
            <span className="text-[13px] tabular-nums text-muted-foreground" aria-hidden="true">
              {cities.length} / {maxCities}
            </span>
          )}
        </div>
        {single ? (
          <CityInput
            id={`${idPrefix}-city`}
            countryCode={countryCode}
            value={cities[0] || ''}
            onChange={(value) => onCitiesChange(value ? [value] : [])}
            onPick={(value) => onCitiesChange([value])}
          />
        ) : (
          <>
            {cities.length ? (
              <ul className="flex flex-wrap gap-2" aria-label={t('searches.cities')}>
                {cities.map((city) => (
                  <li key={city} className="flex min-h-11 max-w-full items-center gap-1.5 rounded-[10px] bg-primary-soft pl-3 text-[15px] text-foreground">
                    <MapPin className="h-4 w-4 shrink-0 text-chip-foreground" aria-hidden="true" />
                    <span className="min-w-0 [overflow-wrap:anywhere]">{city}</span>
                    <button
                      type="button"
                      onClick={() => onCitiesChange(cities.filter((c) => c !== city))}
                      aria-label={t('common.removeItem').replace('{item}', city)}
                      className="flex h-11 w-10 shrink-0 items-center justify-center rounded-[10px] text-chip-foreground hover:bg-primary/10"
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            {cities.length < maxCities ? (
              <CityInput
                id={`${idPrefix}-city`}
                countryCode={countryCode}
                adder
                placeholder={t('searches.addCity')}
                onPick={(value) => {
                  if (!cities.some((c) => c.toLowerCase() === value.toLowerCase())) onCitiesChange([...cities, value])
                }}
              />
            ) : null}
          </>
        )}
        {hint ? <p className="text-[13px] leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
    </div>
  )
}

// Campo città con suggerimenti. `adder`: il testo si svuota dopo la scelta
// (aggiunge un chip); senza, il valore è la città stessa (campo singolo).
function CityInput({ id, countryCode, value, onChange, onPick, adder = false, placeholder }) {
  const [draft, setDraft] = useState(adder ? '' : value)
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const timer = useRef(null)
  const box = useRef(null)

  useEffect(() => {
    if (!adder) setDraft(value)
  }, [adder, value])

  useEffect(() => {
    function outside(event) {
      if (box.current && !box.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [])

  function type(next) {
    setDraft(next)
    if (!adder) onChange(next)
    clearTimeout(timer.current)
    if (next.trim().length < 2) {
      setSuggestions([])
      setOpen(false)
      return
    }
    timer.current = setTimeout(async () => {
      try {
        const results = await autocompleteCity(next, countryCode)
        setSuggestions(results)
        setOpen(results.length > 0)
      } catch {
        setSuggestions([])
      }
    }, DEBOUNCE_MS)
  }

  function pick(city) {
    onPick(city)
    setDraft(adder ? '' : city)
    setSuggestions([])
    setOpen(false)
  }

  const Icon = adder ? Plus : MapPin
  return (
    <div ref={box} className="relative">
      <Icon className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <input
        id={id}
        value={draft}
        autoComplete="off"
        placeholder={placeholder}
        onChange={(event) => type(event.target.value)}
        onFocus={() => setOpen(suggestions.length > 0)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && adder) {
            event.preventDefault()
            if (draft.trim()) pick(draft.trim())
          }
        }}
        className="flex h-12 w-full min-w-0 rounded-field border border-input bg-card pl-11 pr-3.5 text-base text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20"
      />
      {open ? (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-field border border-border bg-card shadow-popover">
          {suggestions.map((suggestion, index) => (
            <li key={`${suggestion.city}-${index}`}>
              <button
                type="button"
                className="flex min-h-11 w-full flex-col justify-center px-3.5 py-2 text-left text-[15px] hover:bg-tint"
                onClick={() => pick(suggestion.city)}
              >
                <span className="font-semibold text-foreground">{suggestion.city}</span>
                <span className="text-xs text-muted-foreground">{suggestion.country}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
