import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { withRetry } from '../utils/retry'

// Stato e azioni della chat di un editor (Sprint 76): prima era dentro i
// pannelli CvDraftChatPanel / CoverLetterChatPanel, che restavano montati a
// pannello chiuso; ora il pannello cambia contenitore (colonna da 1024 px,
// pannello dal basso sotto), quindi lo stato vive nella pagina, sempre
// montata, e il pannello è solo presentazione. Stesso flusso di prima:
// GET cronologia + prezzo/saldo (Sprint 69), invio con salvataggio della
// bozza prima (onBeforeSend), proposta → Accetta/Rifiuta persistita sul
// server con tentativi (Sprint 62/69), 402 = credito insufficiente.
//
// `api` = { fetchChat(jobId), sendMessage(jobId, message), recordDecision(jobId, m, a, d) }
// `t` per i testi degli avvisi; `onApplyAction(action)` → false se
// l'elemento non c'è più; `enabled` false finché la bozza non è caricata.
export function useDraftChat({ jobId, api, t, onApplyAction, onBeforeSend, enabled = true }) {
  const [pricing, setPricing] = useState(null)
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  // Avvisi mostrati nel flusso della conversazione, dopo il turno a cui si
  // riferiscono (mockup `cv-assistant-warn`). Non persistiti, come prima.
  const [notices, setNotices] = useState([])
  const [decisions, setDecisions] = useState({})
  const noticeId = useRef(0)
  const historyLength = useRef(0)
  historyLength.current = history.length

  // `enabled`: si carica quando la bozza esiste (aperta o riseminata dalla
  // pagina), come prima, quando il pannello si montava dopo il caricamento.
  useEffect(() => {
    if (!enabled) return
    api
      .fetchChat(jobId)
      .then((data) => {
        if (data.price != null) setPricing({ price: data.price, balance: data.balance })
        const loadedHistory = data.history || []
        setHistory(loadedHistory)
        const loadedDecisions = {}
        loadedHistory.forEach((turn, messageIndex) => {
          ;(turn.actions || []).forEach((action, actionIndex) => {
            if (action.decision) loadedDecisions[`${messageIndex}-${actionIndex}`] = action.decision
          })
        })
        setDecisions(loadedDecisions)
      })
      .catch(() => {})
    // `api` è un oggetto costante del chiamante.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, enabled])

  function addNotice(variant, text) {
    noticeId.current += 1
    const notice = { id: noticeId.current, variant, text, afterIndex: historyLength.current - 1 }
    setNotices((current) => [...current, notice])
  }

  async function send(extra) {
    const message = input.trim()
    if (!message || sending) return
    setSending(true)
    try {
      if (onBeforeSend) await onBeforeSend()
      const { reply, actions, balance } = await api.sendMessage(jobId, message, extra)
      setHistory((current) => [...current, { role: 'user', message }, { role: 'assistant', message: reply, actions }])
      if (balance != null) setPricing((current) => (current ? { ...current, balance } : current))
      setInput('')
    } catch (err) {
      addNotice('error', err instanceof ApiError && err.status === 402 ? t('cvEditor.chatErrorCredit') : t('cvEditor.chatErrorGeneric'))
    } finally {
      setSending(false)
    }
  }

  function decide(messageIndex, actionIndex, action, choice) {
    let decision = choice
    if (decision === 'accepted' && onApplyAction(action) === false) {
      // Elemento non più presente nella bozza (Sprint 69): niente da
      // applicare, la proposta viene registrata come rifiutata.
      addNotice('note', t('cvEditor.chatTargetMissing'))
      decision = 'rejected'
    }
    setDecisions((current) => ({ ...current, [`${messageIndex}-${actionIndex}`]: decision }))
    withRetry(() => api.recordDecision(jobId, messageIndex, actionIndex, decision)).catch(() =>
      addNotice('note', t('cvEditor.chatDecisionSaveFailed')),
    )
  }

  // Credito insufficiente per il prossimo messaggio: dai dati dell'API
  // (prezzo e saldo), nessun valore scritto nel codice.
  const insufficientCredit = pricing != null && Number(pricing.balance) < Number(pricing.price)

  return { pricing, history, input, setInput, sending, notices, decisions, send, decide, insufficientCredit }
}
