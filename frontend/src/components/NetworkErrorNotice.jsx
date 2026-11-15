import { useEffect, useRef } from 'react'
import { NETWORK_ERROR_EVENT } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useToast } from './ToastProvider'

// Sprint 80 (stato "errore di rete", DESIGN.md §7): molte pagine mostrano il
// messaggio generico quando una richiesta fallisce; se la causa è la rete,
// un avviso lo dice ("Connessione non riuscita…"), al massimo uno ogni 5 s.
export default function NetworkErrorNotice() {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const last = useRef(0)
  useEffect(() => {
    function handle() {
      const now = Date.now()
      if (now - last.current < 5000) return
      last.current = now
      showToast(t('common.networkError'))
    }
    window.addEventListener(NETWORK_ERROR_EVENT, handle)
    return () => window.removeEventListener(NETWORK_ERROR_EVENT, handle)
  }, [showToast, t])
  return null
}
