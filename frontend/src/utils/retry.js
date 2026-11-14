// Ritenta una chiamata fallita (Sprint 69: registrazione delle decisioni
// della chat, prima persa in silenzio se la rete falliva una volta).
export async function withRetry(fn, attempts = 3, delayMs = 800) {
  let lastError
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      if (attempt < attempts - 1) await new Promise((resolve) => setTimeout(resolve, delayMs * (attempt + 1)))
    }
  }
  throw lastError
}

export function formatEuro(value, lang) {
  const number = Number(value)
  if (Number.isNaN(number)) return value
  return number.toLocaleString(lang === 'en' ? 'en-GB' : 'it-IT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}
