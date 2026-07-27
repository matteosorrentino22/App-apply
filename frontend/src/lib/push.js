// Notifiche Web Push (02-specifiche-tecniche-v3.md §3.8, §3.3): nessuna
// libreria dedicata, solo le Web API standard (Notification, PushManager) —
// coerente con "preferire soluzioni standard" (CLAUDE.md).

export function isPushSupported() {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

// iPadOS 13+ si presenta come "Mac" nello user agent ma è touch: nessuna API
// di feature-detection copre questo caso, serve controllare esplicitamente.
export function isIOS() {
  if (typeof navigator === 'undefined') return false
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  )
}

// Su iOS Safari le notifiche push funzionano solo per una PWA aggiunta alla
// schermata Home (§3.3 tecniche): questo distingue quel caso da una scheda
// Safari normale, dove la richiesta di permesso fallirebbe silenziosamente.
export function isStandalone() {
  if (typeof window === 'undefined') return false
  return window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)))
}

export async function subscribeToPush(vapidPublicKey) {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    return { status: permission }
  }

  const registration = await navigator.serviceWorker.ready
  let subscription = await registration.pushManager.getSubscription()
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    })
  }
  return { status: 'granted', subscription }
}
