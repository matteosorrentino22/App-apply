export function formatEuro(value, lang = 'it') {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat(lang === 'en' ? 'en-IE' : 'it-IT', { style: 'currency', currency: 'EUR' }).format(
    amount,
  )
}
