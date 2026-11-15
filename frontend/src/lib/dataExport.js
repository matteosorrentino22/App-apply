import { useState } from 'react'
import { requestDataExport } from '../api/auth'
import { ApiError } from '../api/client'

// Export dei dati (Sprint 67): richiede il link firmato allo ZIP e lo apre.
// Hook condiviso dal pulsante (schermata di accettazione) e dalla riga di
// "Privacy e sicurezza" (Sprint 78). `onError(messageKey)` per l'avviso.
export function useDataExport(onError) {
  const [busy, setBusy] = useState(false)
  async function exportData() {
    setBusy(true)
    try {
      const url = await requestDataExport()
      window.location.assign(url)
    } catch (err) {
      onError(err instanceof ApiError && err.status === 429 ? 'account.exportTooMany' : 'common.genericError')
    } finally {
      setBusy(false)
    }
  }
  return { busy, exportData }
}
