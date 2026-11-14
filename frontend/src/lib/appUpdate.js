// Nuova versione della PWA (Sprint 70, §11.33 tecniche). Il service worker
// nuovo si attiva subito (`skipWaiting` + `clients.claim` in sw.js), ma la
// scheda aperta continua a eseguire il bundle già caricato: invece di
// ricaricarla da sola (si perderebbero modifiche non salvate) l'app mostra
// "Nuova versione disponibile — Aggiorna" e ricarica solo su richiesta.
//
// La registrazione è fatta qui e non con `virtual:pwa-register` di
// vite-plugin-pwa: quello, anche in modalità 'prompt', ricarica la pagina
// quando prende il controllo un service worker trovato da un controllo
// successivo o da un'altra scheda (evento "controlling" di workbox-window).
export const APP_UPDATE_EVENT = 'app-apply:update-available'

// Le schede aperte a lungo (PWA in background su iOS) non ricontrollano il
// service worker da sole: controllo periodico e al ritorno in primo piano.
const UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1000

let updateAvailable = false

export function isAppUpdateAvailable() {
  return updateAvailable
}

export function registerServiceWorker() {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return
  // Alla prima visita il service worker prende il controllo di una pagina
  // che non ne aveva: non è un aggiornamento.
  let controlled = Boolean(navigator.serviceWorker.controller)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (controlled && !updateAvailable) {
      updateAvailable = true
      window.dispatchEvent(new Event(APP_UPDATE_EVENT))
    }
    controlled = true
  })

  // Solo nella build: in sviluppo il service worker non esiste
  // (devOptions.enabled: false in vite.config.js).
  if (!import.meta.env.PROD) return
  navigator.serviceWorker
    .register('/sw.js', { scope: '/' })
    .then((registration) => {
      const check = () => registration.update().catch(() => {})
      setInterval(check, UPDATE_CHECK_INTERVAL_MS)
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') check()
      })
    })
    .catch(() => {})
}
