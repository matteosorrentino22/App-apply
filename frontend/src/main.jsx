import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { registerServiceWorker } from './lib/appUpdate'

// Service worker e avviso di nuova versione, senza ricaricamenti automatici
// (Sprint 70, lib/appUpdate.js).
registerServiceWorker()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
