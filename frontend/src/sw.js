import { precacheAndRoute } from 'workbox-precaching'

// Precache dei soli asset statici di build (installabilità PWA). Nessuna
// runtimeCaching per /api: le chiamate API vanno sempre in rete, mai in
// cache (CLAUDE.md: no cache offline dei dati).
precacheAndRoute(self.__WB_MANIFEST)

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  if (!event.data) return
  let payload
  try {
    payload = event.data.json()
  } catch {
    payload = { title: 'App-apply', body: event.data.text() }
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || 'App-apply', {
      body: payload.body,
      icon: '/pwa-192x192.png',
      data: { url: payload.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus()
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl)
      }
    }),
  )
})
