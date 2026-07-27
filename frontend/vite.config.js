import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

const backendProxy = {
  '/api': { target: backendTarget, changeOrigin: true },
  '/accounts': { target: backendTarget, changeOrigin: true },
  '/admin': { target: backendTarget, changeOrigin: true },
  '/media': { target: backendTarget, changeOrigin: true },
  '/static': { target: backendTarget, changeOrigin: true },
}

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
      },
      manifest: {
        name: 'App-apply',
        short_name: 'App-apply',
        description: 'Centralizza e automatizza la ricerca di lavoro',
        theme_color: '#6b4a2e',
        background_color: '#fbf8f2',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
  server: {
    // Il dev server non è esposto direttamente a Internet (raggiungibile
    // solo da Caddy dentro la rete Docker interna, nessuna porta pubblicata
    // in docker-compose.yml): l'allowlist host di Vite va quindi disattivata,
    // altrimenti rifiuta le richieste proxate con l'header Host originale
    // (dominio/IP del VPS) non presente nella whitelist di default.
    allowedHosts: true,
    proxy: backendProxy,
  },
  // Serve la build di produzione in locale (`vite preview`): a differenza
  // del dev server, qui il service worker è davvero attivo — necessario per
  // testare il flusso di sottoscrizione alle notifiche push (Sprint 20),
  // disabilitato in dev (`devOptions.enabled: false` sopra) per non
  // interferire con l'HMR.
  preview: {
    allowedHosts: true,
    proxy: backendProxy,
  },
})
