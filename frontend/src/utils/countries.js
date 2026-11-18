// Elenco dei paesi (Sprint 84, A17): codici ISO 3166-1 e nomi dal browser
// (`Intl.DisplayNames`), nessuna dipendenza. Nell'interfaccia il nome è nella
// lingua dell'utente; verso il server e la fonte sempre in inglese (come le
// città dell'autocomplete, Nominatim con accept-language=en).
const CODES = (
  'AD AE AF AG AL AM AO AR AT AU AZ BA BB BD BE BF BG BH BI BJ BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CL CM CN CO CR CU CV CY CZ ' +
  'DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FM FR GA GB GD GE GH GM GN GQ GR GT GW GY HK HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP ' +
  'KE KG KH KI KM KN KR KW KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MO MR MT MU MV MW MX MY MZ NA NE NG NI NL ' +
  'NO NP NR NZ OM PA PE PG PH PK PL PR PS PT PW PY QA RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SY SZ TD TG TH TJ TL ' +
  'TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VN VU WS XK YE ZA ZM ZW'
).split(' ')

function displayNames(lang) {
  try {
    return new Intl.DisplayNames([lang], { type: 'region' })
  } catch {
    return null
  }
}

const english = displayNames('en')

export function englishCountryName(code) {
  return (english && english.of(code)) || code
}

// [{ code, name (inglese, salvato), label (lingua dell'interfaccia) }],
// ordinati per etichetta.
export function countryOptions(lang) {
  const local = displayNames(lang)
  return CODES.map((code) => ({ code, name: englishCountryName(code), label: (local && local.of(code)) || englishCountryName(code) }))
    .sort((a, b) => a.label.localeCompare(b.label, lang))
}

// Codice ISO dal nome inglese salvato (ricerche esistenti), o ''.
export function countryCodeFor(name) {
  if (!name) return ''
  const target = name.trim().toLowerCase()
  return CODES.find((code) => englishCountryName(code).toLowerCase() === target) || ''
}

export function countryLabel(name, lang) {
  const code = countryCodeFor(name)
  const local = code ? displayNames(lang) : null
  return (local && local.of(code)) || name
}
