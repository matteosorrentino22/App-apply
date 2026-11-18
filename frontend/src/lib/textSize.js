// Dimensione del testo (Sprint 84, SPEC-DELTA A20, mockup
// `settings-dimensione-testo`): scelta del dispositivo (localStorage, non sul
// server). Ingrandisce tutta l'app con `zoom` sul documento: testo, pulsanti,
// icone e spazi (molte misure sono in px, non solo in rem), e la pagina si
// ridispone sulla larghezza dello schermo senza scorrimento laterale (con una
// larghezza utile di almeno MIN_LAYOUT_WIDTH px).
// "Come il telefono": su iPhone/iPad segue la dimensione del testo di sistema
// (font dinamico `-apple-system-body`, 17 px a dimensione standard), anche
// nell'app aggiunta alla Home dove non c'è lo zoom di Safari; sugli altri
// sistemi il browser applica già da sé l'impostazione del sistema.

export const TEXT_SIZES = ['system', 'normal', 'large']
const STORAGE_KEY = 'appapply.textSize'
const LARGE_ZOOM = 1.2
const IOS_BODY_DEFAULT_PX = 17
const MIN_ZOOM = 0.85
const MAX_ZOOM = 1.4
// Sotto i 300 px di larghezza utile la navigazione e le righe dei documenti
// non stanno più nello schermo: su telefoni molto stretti (iPhone SE, 320 px)
// l'ingrandimento si riduce quanto basta.
const MIN_LAYOUT_WIDTH = 300

export function getTextSize() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return TEXT_SIZES.includes(value) ? value : 'system'
  } catch {
    return 'system'
  }
}

function isIOS() {
  const ua = navigator.userAgent || ''
  return /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)
}

function systemZoom() {
  if (!isIOS()) return 1
  const probe = document.createElement('span')
  probe.style.cssText = 'position:absolute;visibility:hidden;font:-apple-system-body'
  probe.textContent = 'A'
  document.body.appendChild(probe)
  const px = parseFloat(getComputedStyle(probe).fontSize)
  probe.remove()
  if (!px) return 1
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, px / IOS_BODY_DEFAULT_PX))
}

export function textSizeZoom(size) {
  const wanted = size === 'large' ? LARGE_ZOOM : size === 'normal' ? 1 : systemZoom()
  if (wanted <= 1) return wanted
  return Math.max(1, Math.min(wanted, window.innerWidth / MIN_LAYOUT_WIDTH))
}

export function applyTextSize(size = getTextSize()) {
  const zoom = textSizeZoom(size)
  const root = document.documentElement
  root.style.zoom = zoom === 1 ? '' : String(Math.round(zoom * 100) / 100)
  root.dataset.textSize = size
}

export function setTextSize(size) {
  try {
    window.localStorage.setItem(STORAGE_KEY, size)
  } catch {
    // Archivio non disponibile (es. navigazione privata): vale solo per la sessione.
  }
  applyTextSize(size)
}

// All'avvio e al ritorno nell'app (l'utente può aver cambiato la dimensione
// del testo nelle impostazioni del telefono).
export function initTextSize() {
  applyTextSize()
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') applyTextSize()
  })
  // Rotazione o finestra ridimensionata: il limite di larghezza cambia.
  window.addEventListener('resize', () => applyTextSize())
}
