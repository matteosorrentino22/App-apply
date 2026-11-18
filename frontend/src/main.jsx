import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { registerServiceWorker } from './lib/appUpdate'
import { initTextSize } from './lib/textSize'

// Service worker e avviso di nuova versione, senza ricaricamenti automatici
// (Sprint 70, lib/appUpdate.js).
registerServiceWorker()
// Dimensione del testo scelta sul dispositivo (Sprint 84, lib/textSize.js).
initTextSize()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
